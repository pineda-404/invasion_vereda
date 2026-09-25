- Colocar el video en `data/video.mp4`

## Instalación

```bash
# 1. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: .\venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt
```

## Ejecución

```bash
# Ejecución con ventana gráfica
python main.py

# Ejecución sin ventana (modo headless / máxima velocidad)
python main.py --no-display
```

## Pipeline de procesamiento digital de imágenes

### 1. Conversión a Escala de Grises

![Escala de Grises](images/pdi_1b_moto_grises.jpg)

### 2. Umbralización Adaptativa Invertida

![Umbral Adaptativo Invertido](images/pdi_2_moto_umbral_adaptativo.jpg)

### 3. Filtro No Lineal de Mediana

![Filtro de Mediana](images/pdi_3_moto_filtro_mediana.jpg)

### 4. Dilatación Morfológica

![Dilatación Morfológica](images/pdi_4_moto_dilatacion_masa.jpg)
