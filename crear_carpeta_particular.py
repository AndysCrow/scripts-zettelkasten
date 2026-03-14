import os
import re
import shutil
from pathlib import Path

# ============================================================
# CONFIGURACIÓN DEL USUARIO (CÁMBIALO AQUÍ)
# ============================================================
# Ruta a la raíz de tu bóveda de Obsidian
RUTA_BOVEDA = Path("/home/andres-crow/Obsidian") # <--- CAMBIA ESTO

# Nombre del archivo de la nota semilla (ej: "202603112112" o "202603112112.md")
NOMBRE_NOTA_SEMILLA = "202603112112" 

# Niveles de profundidad máximos (1 = solo enlaces directos, 2 = enlaces de los enlaces, etc.)
PROFUNDIDAD_MAXIMA = 5

# Carpeta de salida (se creará dentro de RUTA_BOVEDA)
CARPETA_SALIDA = "Rama_Exportada"
# ============================================================

# Patrón para encontrar enlaces de Obsidian: [[ID]] o [[ID|Alias]]
ENLACE_PATTERN = r'\[\[([^\|\]]+)(?:\|[^\]]+)?\]\]'
# Patrón para encontrar imágenes/archivos ![[imagen.png]]
ADJUNTO_PATTERN = r'!\[\[([^\]]+)\]\]'

def encontrar_archivos_markdown(ruta_boveda):
    """Encuentra todos los archivos .md en la bóveda y devuelve un dict {id_sin_extension: ruta_completa}"""
    archivos = {}
    for root, dirs, files in os.walk(ruta_boveda):
        # Ignorar carpetas ocultas y la carpeta de salida si ya existe
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != CARPETA_SALIDA]
        for file in files:
            if file.endswith('.md'):
                ruta_completa = Path(root) / file
                id_nota = file[:-3] # Quitar la extensión .md
                archivos[id_nota] = ruta_completa
    return archivos

def extraer_enlaces_y_adjuntos(ruta_archivo):
    """Lee un archivo .md y devuelve dos sets: uno con los IDs de notas enlazadas y otro con los nombres de archivos adjuntos."""
    enlaces = set()
    adjuntos = set()
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
            # Encontrar enlaces a otras notas
            for match in re.finditer(ENLACE_PATTERN, contenido):
                enlaces.add(match.group(1))
            # Encontrar archivos adjuntos
            for match in re.finditer(ADJUNTO_PATTERN, contenido):
                adjuntos.add(match.group(1))
    except Exception as e:
        print(f"  Error al leer {ruta_archivo}: {e}")
    return enlaces, adjuntos

def rastrear_rama(semilla_id, archivos_dict, profundidad_max, nivel_actual=0, visitados=None, adjuntos_globales=None):
    """Función recursiva para rastrear todas las notas y adjuntos de la rama."""
    if visitados is None:
        visitados = set()
    if adjuntos_globales is None:
        adjuntos_globales = set()

    if nivel_actual > profundidad_max or semilla_id in visitados:
        return visitados, adjuntos_globales

    print(f"{'  ' * nivel_actual}Procesando: {semilla_id} (Nivel {nivel_actual})")
    visitados.add(semilla_id)

    # Obtener la ruta del archivo actual
    ruta_actual = archivos_dict.get(semilla_id)
    if not ruta_actual:
        print(f"{'  ' * nivel_actual}  ¡Error! Archivo no encontrado para ID: {semilla_id}")
        return visitados, adjuntos_globales

    # Extraer enlaces y adjuntos de este archivo
    enlaces, adjuntos = extraer_enlaces_y_adjuntos(ruta_actual)

    # Añadir adjuntos encontrados al conjunto global
    adjuntos_globales.update(adjuntos)

    # Rastrear recursivamente cada enlace
    for enlace_id in enlaces:
        # Asegurarse de que el enlace es un ID de nota (existe en nuestro dict) y no está ya visitado
        if enlace_id in archivos_dict and enlace_id not in visitados:
            sub_visitados, sub_adjuntos = rastrear_rama(
                enlace_id, archivos_dict, profundidad_max, nivel_actual + 1, visitados, adjuntos_globales
            )
            # Los conjuntos se actualizan por referencia, no es necesario re-asignar
        elif enlace_id not in archivos_dict:
            # Es un enlace a algo que no es un archivo .md en la raíz (podría ser un enlace a un archivo en subcarpeta, lo ignoramos por simplicidad o podrías expandir el script)
            # print(f"{'  ' * (nivel_actual+1)}Enlace externo o no .md ignorado: {enlace_id}")
            pass

    return visitados, adjuntos_globales

def copiar_archivos(ids_notas, adjuntos, ruta_boveda, ruta_salida):
    """Copia los archivos .md y los adjuntos a la carpeta de salida."""
    print(f"\nCopiando {len(ids_notas)} notas y {len(adjuntos)} adjuntos a {ruta_salida}...")

    # Crear la carpeta de salida si no existe
    ruta_salida.mkdir(parents=True, exist_ok=True)

    # Copiar archivos .md
    for id_nota in ids_notas:
        origen = ruta_boveda / f"{id_nota}.md"
        destino = ruta_salida / f"{id_nota}.md"
        if origen.exists():
            shutil.copy2(origen, destino)
            print(f"  Nota copiada: {id_nota}.md")
        else:
            print(f"  ¡Advertencia! Nota no encontrada en origen: {id_nota}.md")

    # Copiar archivos adjuntos
    for adjunto in adjuntos:
        # Búsqueda simple: asumimos que los adjuntos están en la raíz o en subcarpetas comunes.
        # Esto busca el archivo por nombre en toda la bóveda. Si hay duplicados, coge el primero.
        # Una versión más avanzada podría buscar en una ruta relativa si se guarda esa info.
        encontrado = False
        for root, dirs, files in os.walk(ruta_boveda):
            if adjunto in files:
                origen = Path(root) / adjunto
                destino = ruta_salida / adjunto
                shutil.copy2(origen, destino)
                print(f"  Adjunto copiado: {adjunto}")
                encontrado = True
                break # Salir del bucle una vez encontrado
        if not encontrado:
            print(f"  ¡Advertencia! Adjunto no encontrado: {adjunto}")

    print("¡Copia completada!")


if __name__ == "__main__":
    print("Iniciando exportación de rama Zettelkasten...")
    print(f"Bóveda: {RUTA_BOVEDA}")
    print(f"Nota Semilla: {NOMBRE_NOTA_SEMILLA}")
    print(f"Profundidad Máxima: {PROFUNDIDAD_MAXIMA}")

    # 1. Indexar todos los archivos .md de la bóveda
    print("\nIndexando archivos Markdown...")
    archivos_md = encontrar_archivos_markdown(RUTA_BOVEDA)
    print(f"Se encontraron {len(archivos_md)} archivos .md.")

    # Limpiar el nombre de la nota semilla (quitar .md si se puso)
    semilla_clean = NOMBRE_NOTA_SEMILLA.replace('.md', '')

    if semilla_clean not in archivos_md:
        print(f"\n¡ERROR! La nota semilla '{semilla_clean}.md' no se encontró en la bóveda.")
        exit()

    # 2. Rastrear la rama recursivamente
    print("\nRastreando la red de notas...")
    notas_afectadas, adjuntos_afectados = rastrear_rama(
        semilla_clean, archivos_md, PROFUNDIDAD_MAXIMA
    )

    print(f"\nResumen del rastreo:")
    print(f"  Notas encontradas: {len(notas_afectadas)}")
    print(f"  Adjuntos encontrados: {len(adjuntos_afectados)}")

    # 3. Copiar los archivos a la carpeta de salida
    ruta_salida_completa = RUTA_BOVEDA / CARPETA_SALIDA
    copiar_archivos(notas_afectadas, adjuntos_afectados, RUTA_BOVEDA, ruta_salida_completa)

    print("\n✅ Proceso finalizado.")
    print(f"Ahora puedes usar el plugin 'Webpage HTML Export' sobre la carpeta: {ruta_salida_completa}")
