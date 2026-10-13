import os

# Ajuste para las camaras RTSP: se pide que el video viaje por un canal mas
# seguro (TCP). Con el otro canal (UDP) se pierden datos y la imagen puede
# verse gris o con errores. Se pone aqui porque tiene que quedar listo
# antes de abrir cualquier camara.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
