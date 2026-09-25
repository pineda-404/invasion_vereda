import os
import sys
import json
import argparse
import numpy as np
import cv2

# coordenadas de la vereda (x, y, ancho, alto)
ROI = (294, 258, 282, 149)


# configuracion de argumentos
def parse_args():
    parser = argparse.ArgumentParser(
        description="Deteccion y conteo de vehiculos invasores en vereda"
    )
    parser.add_argument("--video", default="data/video.mp4")
    parser.add_argument("--reporte", default="output/reporte.json")
    parser.add_argument("--no-display", action="store_true")
    parser.add_argument(
        "--umbral-vehiculo", dest="umbral_vehiculo", type=int, default=13200
    )
    parser.add_argument("--umbral-peaton", type=int, default=8500)
    parser.add_argument("--umbral-reset", type=int, default=8200)
    parser.add_argument("--cooldown-sec", type=float, default=1.0)
    parser.add_argument("--min-cols-vehiculo", type=int, default=235)
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.exists(args.video):
        print(f"Error: no se encuentra el video en {args.video}")
        sys.exit(1)

    # coordenadas roi
    x, y, w, h = ROI

    # captura de video
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: no se pudo abrir {args.video}")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    duracion_segundos = total_frames / fps if total_frames > 0 else 0
    duracion_minutos = duracion_segundos / 60.0

    # kernel morfologico
    kernel = np.ones((5, 5), np.uint8)

    # variables de conteo y maquina de estados
    contador_vehiculos = 0
    vehiculo_en_zona = False
    cooldown_frames = 0
    cooldown_max = int(round(fps * args.cooldown_sec))
    frame_idx = 0
    registro_eventos = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            tiempo_actual_sec = frame_idx / fps

            if cooldown_frames > 0:
                cooldown_frames -= 1

            # conversion a escala de grises
            img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # umbral adaptativo invertido
            img_th = cv2.adaptiveThreshold(
                img_gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                25,
                16,
            )

            # filtro de mediana
            img_median = cv2.medianBlur(img_th, 5)

            # dilatacion morfologica
            img_dil = cv2.dilate(img_median, kernel)

            # recorte roi y conteo de masa
            espacio = img_dil[y : y + h, x : x + w]
            count = cv2.countNonZero(espacio)

            # perfil de proyeccion vertical
            col_density = np.sum(espacio > 0, axis=0)
            cols_activas = int(np.sum(col_density > 25))

            # clasificacion y maquina de estados
            es_vehiculo = (count >= args.umbral_vehiculo) and (
                cols_activas >= args.min_cols_vehiculo
            )

            if es_vehiculo:
                color_roi = (0, 0, 255)
                estado_texto = f"!VEHICULO INVASOR! ({count} px)"

                if not vehiculo_en_zona and cooldown_frames == 0:
                    contador_vehiculos += 1
                    vehiculo_en_zona = True
                    cooldown_frames = cooldown_max
                    tiempo_str = f"{int(tiempo_actual_sec // 60):02d}:{int(tiempo_actual_sec % 60):02d}"
                    print(
                        f"[ALERTA INVASION #{contador_vehiculos:02d}] Segundo {tiempo_str} ({tiempo_actual_sec:.1f}s)"
                    )
                    registro_eventos.append(
                        {
                            "numero": contador_vehiculos,
                            "segundo": round(tiempo_actual_sec, 2),
                            "pixeles": count,
                            "cols_activas": cols_activas,
                        }
                    )
            else:
                if count < args.umbral_reset:
                    vehiculo_en_zona = False
                color_roi = (0, 255, 0)
                estado_texto = f"Vereda Libre ({count} px)"

            # visualizacion en pantalla
            if not args.no_display:
                # dibujo de marcadores en frame
                cv2.rectangle(frame, (x, y), (x + w, y + h), color_roi, 2)
                cv2.putText(
                    frame,
                    estado_texto,
                    (x, max(20, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    color_roi,
                    2,
                )

                # panel superior de informacion
                cv2.rectangle(frame, (10, 10), (430, 80), (0, 0, 0), -1)
                cv2.rectangle(frame, (10, 10), (430, 80), (255, 255, 255), 1)
                cv2.putText(
                    frame,
                    f"VEHICULOS INVASORES: {contador_vehiculos}",
                    (20, 42),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                )
                min_act, sec_act = (
                    int(tiempo_actual_sec // 60),
                    int(tiempo_actual_sec % 60),
                )
                min_tot, sec_tot = (
                    int(duracion_segundos // 60),
                    int(duracion_segundos % 60),
                )
                cv2.putText(
                    frame,
                    f"Tiempo: {min_act:02d}:{sec_act:02d} / {min_tot:02d}:{sec_tot:02d} | Pixeles: {count}",
                    (20, 68),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (200, 200, 200),
                    1,
                )

                cv2.imshow("Monitoreo Vereda", frame)
                if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                    break

    finally:
        cap.release()
        if not args.no_display:
            cv2.destroyAllWindows()

    # metricas finales
    minutos_analizados = (
        duracion_minutos if duracion_minutos > 0 else (frame_idx / fps / 60.0)
    )
    tasa_vehiculos_minuto = (
        contador_vehiculos / minutos_analizados if minutos_analizados > 0 else 0
    )
    vehiculos_proyectados_hora = int(round(tasa_vehiculos_minuto * 60))

    # reporte json
    if args.reporte:
        os.makedirs(os.path.dirname(args.reporte), exist_ok=True)
        with open(args.reporte, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total_vehiculos": contador_vehiculos,
                    "tasa_por_minuto": round(tasa_vehiculos_minuto, 2),
                    "proyeccion_hora": vehiculos_proyectados_hora,
                    "eventos": registro_eventos,
                },
                f,
                indent=2,
            )

    # salida en consola
    print(f"Total de vehiculos invasores: {contador_vehiculos}")
    print(f"Tasa de invasion: {tasa_vehiculos_minuto:.2f} vehiculos/minuto")
    print(f"Proyeccion hora punta: {vehiculos_proyectados_hora} vehiculos/hora")


if __name__ == "__main__":
    main()
