# 🎬 RAGNAVOD: Laboratorio de Streaming VOD & Análisis de Protocolos (QUIC vs. TCP)

[![Protocol](https://img.shields.io/badge/Protocols-HTTP%2F3%20(QUIC)%20%7C%20HTTP%2F2%20(TCP)-blue.svg)](#)
[![OS](https://img.shields.io/badge/Server%20OS-Rocky%20Linux%209-green.svg)](#)
[![Router](https://img.shields.io/badge/Networking-MikroTik%20RouterOS%20v7-orange.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](#)

RAGNAVOD es un banco de pruebas experimental y plataforma de Video-on-Demand (VOD) de alto rendimiento desplegada sobre infraestructura física local. El objetivo central del proyecto es evaluar de manera empírica las diferencias de desempeño, resiliencia y sobrecarga de procesamiento entre la capa de transporte tradicional **TCP (HTTP/2)** y el protocolo emergente **QUIC sobre UDP (HTTP/3)**, analizando la mitigación del bloqueo de cabeza de línea (*Head-of-Line Blocking* - HOLB) en escenarios de red adversos.

---

## 📌 1. Visión General del Proyecto

En transmisiones multimedia de alta definición, la estabilidad de la capa de transporte determina directamente la Calidad de Experiencia (QoE). Mientras que HTTP/2 multiplexa múltiples flujos sobre un único socket TCP, cualquier pérdida de paquetes en el canal físico (especialmente enlaces Wi-Fi con interferencia RF) detiene la entrega de datos hasta que el segmento es retransmitido.

**RAGNAVOD** implementa una arquitectura desacoplada para auditar este fenómeno:
- **Capa de Transporte & Proxy L7:** Caddy v2 gestiona la negociación de HTTP/3, TLS 1.3 y despacha fragmentos multimedia pre-codificados directamente desde el almacenamiento local.
- **Resolución Soberana:** Servidor BIND 9 con arquitectura *Split-Horizon* y registros HTTPS (Type 65) con soporte ALPN `h3`.
- **Backend & Telemetría:** FastAPI (Python asíncrono) actuando como colector de telemetría (*Sink*) de métricas enviadas por el sensor del reproductor Hls.js en tiempo real.
- **Red Aislada:** Segmentación perimetral estricta en Capa 2/3 mediante MikroTik RouterOS.

---

## 🏗️ 2. Arquitectura de Infraestructura

El laboratorio fue desplegado en hardware local evitando la abstracción de servicios en la nube, permitiendo capturar el comportamiento crudo de los paquetes sobre interfaces físicas.

```text
                              [ Internet ]
                                    │
                                    ▼ WAN Física
                        ┌───────────────────────┐
                        │   Router ISP (CGNAT)  │  (Puertos 22, 80, 443 bloqueados)
                        └───────────────────────┘
                                    │ DHCP Privado (Doble NAT)
                                    ▼ ether1
                        ┌───────────────────────┐
                        │    MikroTik Router    │  (Central Gateway & L2 Bridge Filtering)
                        │     RouterOS v7       │  FastTrack deshabilitado
                        └───────────────────────┘
                           │                 │
     ether5 (VLAN 4 Untagged)│                 │ ether2-4 / wlan1 (PVID 1)
                           ▼                 ▼
             ┌────────────────────────┐   ┌────────────────────────┐
             │ Servidor Rocky Linux 9 │   │  Estación de Pruebas   │
             │   IP: 172.16.10.10     │   │   (Cliente Chromium)   │
             │ Caddy | BIND | FastAPI │   │   Subred 192.168.88.x  │
             └────────────────────────┘   └────────────────────────┘
             [    DMZ LÓGICA ESTRICTA   ]   [  SEGMENTO LAN / WI-FI  ]
```

### Segmentación L2/L3 y Seguridad
- **VLAN 4 (RAGNAVOD):** Segmento dedicado en subred `172.16.10.0/24` asociado al puerto físico `ether5` (Access/Untagged). La IP del gateway MikroTik reside en `172.16.10.1`.
- **Aislamiento DMZ:** Reglas en la cadena `forward` del firewall de MikroTik que permiten tráfico entrante desde la LAN hacia los servicios de la DMZ (80, 443 TCP/UDP, 53 UDP/TCP), pero ejecutan un **DROP estricto** ante cualquier intento de conexión iniciado desde la DMZ hacia la red doméstica privada (`192.168.88.0/24`).
- **Nivelación Experimental (FastTrack Off):** Se inhabilitó la directiva `fasttrack-connection` de MikroTik para evitar que TCP obtuviera ventajas artificiales por bypass del CPU del router, forzando a que tanto TCP como UDP compitieran bajo el mismo costo de inspección.

### Servicios Core en el Servidor (`172.16.10.10`)
1. **BIND 9 (Split-Horizon DNS):** Resuelve `ragnavod.lan` directamente hacia `172.16.10.10` e inyecta el registro `HTTPS` (Type 65) con parámetro `alpn="h3"` para habilitar el descubrimiento inmediato del canal QUIC.
2. **Caddy Proxy:** Escucha en `443/tcp` y `443/udp`. Provee terminación criptográfica TLS 1.3 vía CA local interna, despacha estáticos desde `/var/www/ragnavod_data/streams` y emite la cabecera:
   ```http
   Alt-Svc: h3=":443"; ma=86400
   ```
3. **FastAPI & Uvicorn:** Demonio persistente en systemd (`ragnavod.service`) escuchando en `127.0.0.1:8000` dedicado al enrutamiento de la interfaz y persistencia del colector de telemetría.

---

## 🧱 3. Desafíos de Red en Escenarios Reales (El Factor ISP)

El despliegue en un entorno residencial conllevó restricciones de conectividad de borde:

| Restricción Técnica | Impacto en el Proyecto | Solución de Ingeniería |
| :--- | :--- | :--- |
| **Doble NAT & Router ISP Bloqueado** | Imposibilidad de configurar Modo Puente (*Bridge Mode*) y tráfico entrante descartado. | Enrutamiento perimetral inter-VLAN en MikroTik aislando el servidor en una DMZ local soberana. |
| **CGNAT (RFC 6598)** | Rango `100.64.0.0/10` sin IP pública individual direccionable. | Anulación de dependencias de internet; resolución local autoritativa con BIND y certificados emitidos por CA interna. |
| **Bloqueo de Puerto 22/SSH Entrante** | Cancelación de flujos de CI/CD clásicos tipo *Push* (ej. GitHub Actions conectando al servidor). | Adopción de una estrategia de despliegue sincronizado **Pull-based** vía scripts de actualización forzada. |

### Flujo de Despliegue (*Pull-Based Deployment*)
Al no tener visibilidad SSH externa, las actualizaciones en el servidor se ejecutan de manera determinista:

```bash
cd /opt/ragnavod
git fetch --all
git reset --hard origin/main
sudo chown -R rvod:rvod /opt/ragnavod
sudo systemctl restart ragnavod
```

---

## 🧪 4. Telemetría y Experimento

### Sensor Multimedia y Pipeline
- **Material de Muestra:** Tráiler oficial de *Dune: Part Two*, transcodificado mediante FFmpeg a resolución 1080p (1920x1080) a 24 fps, segmentado en fragmentos HLS constantes de 4 segundos (`.m3u8` y `.ts`).
- **Instrumentación del Frontend:** Hooks en JavaScript integrados con la API de eventos de `Hls.js` que capturan las marcas de tiempo de red en cada segmento y transmiten periódicamente un payload JSON al endpoint `/api/log_metrics`.

### Métricas Auditadas
1. **Time to First Frame (TTFF):** Latencia inicial de arranque desde la acción de reproducción hasta el despliegue del primer fotograma:
   $$T_{\text{TTFF}} = T_{\text{FirstFrameRendered}} - T_{\text{PlayRequest}}$$
2. **Fragment Load Time (FLT):** Duración de la transferencia a nivel de socket de cada fragmento `.ts`:
   $$T_{\text{FLT}} = T_{\text{FragmentReceived}} - T_{\text{FragmentRequested}}$$
3. **Inter-Arrival Jitter ($J_{\text{inter}}$):** Variación paso a paso en el tiempo de arribo entre fragmentos adyacentes ($n$ y $n-1$), midiendo la estabilidad instantánea del canal:
   $$J_{\text{inter}} = \big| (R_n - R_{n-1}) - (S_n - S_{n-1}) \big|$$
4. **Steady State Jitter ($\sigma_{\text{jitter}}$):** Desviación estándar acumulada de los tiempos de carga en régimen permanente.
5. **Eventos de Rebuffering:** Conteo de interrupciones por vaciado de buffer de reproducción.

---

## 📊 5. Resultados y Conclusiones

Los datos extraídos del colector (`metrics.csv`) durante las corridas de prueba arrojaron los siguientes resultados consolidados:

| Indicador Evaluado | HTTP/3 (QUIC / UDP) | HTTP/2 (TCP) | Análisis Técnico del Comportamiento |
| :--- | :---: | :---: | :--- |
| **TTFF Promedio** | $224.17\text{ ms}$ | **$196.88\text{ ms}$** | TCP arranca más rápido en LAN debido a la madurez de los sockets del kernel de Linux; QUIC asume mayor costo criptográfico inicial en espacio de usuario. |
| **FLT en Régimen Estable** | **$85.12 - 94.58\text{ ms}$** | $47.38 - 96.64\text{ ms}$ | QUIC ofrece una entrega sumamente plana y predecible. TCP exhibe fluctuaciones abruptas por control de congestión y ventanas de ACK. |
| **Inter-Arrival Jitter** | **$32.27 - 41.72\text{ ms}$** | $42.00 - 53.90\text{ ms}$ | QUIC atenúa los picos de latencia. TCP sufre ante micro-pérdidas en el medio inalámbrico debido a HOLB. |
| **Steady State Jitter** | **$38.50\text{ ms}$** | $42.00\text{ ms}$ | Menor dispersión estadística global en la sesión multimedia con QUIC. |
| **Eventos de Rebuffering** | **0** | **0** | Reproducción continua sin congelamientos en ambos protocolos bajo el ancho de banda de la VLAN. |

### Hallazgos Principales

1. **Inmunidad al Head-of-Line Blocking (HOLB):**  
   Bajo HTTP/2 sobre TCP, un datagrama perdido en el enlace inalámbrico detiene la entrega de todos los flujos multiplexados concurrentes. En cambio, QUIC aísla los flujos a nivel de datagramas UDP independientes; la pérdida de un paquete no interrumpe la carga de fragmentos en paralelo, eliminando el patrón en "diente de sierra" observado en TCP.

2. **Costo de Silicio (CPU Overhead en User-Space):**  
   La inspección del controlador de red del servidor confirmó:
   ```bash
   [rvod@ragnavodServer ~]$ ethtool -k enp1s0 | grep udp-segmentation
   udp-segmentation-offload: off
   ```
   A diferencia de TCP, respaldado por décadas de optimización mediante *TCP Segmentation Offload* (TSO) directo en la tarjeta de red, QUIC opera en el espacio de usuario (Caddy / Go). En el procesador Intel Core i5 M 480 (sin aceleración USO por hardware), cada datagrama UDP debió ser segmentado y cifrado por la CPU principal, evidenciando el compromiso técnico entre resiliencia de transporte y demanda de cómputo en hardware heredado.


---

## 👨‍💻 Autor
- **Matías Rivera
