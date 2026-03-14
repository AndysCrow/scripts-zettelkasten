import os
import re
import glob
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def es_nota_indice(id_nota, titulo, ruta):
    """
    Detecta si una nota es un índice basado en el nombre del archivo
    """
    nombre_archivo = Path(ruta).stem
    
    # Patrón para tus índices: "1. INDICE - SO", "2. INDICE - Redes", etc.
    # También captura si tienen comillas o caracteres especiales
    patron_indice = r'^\d+\.?\s*INDICE\s*-'
    
    if re.search(patron_indice, nombre_archivo, re.IGNORECASE):
        return True
    
    # Verificar también el título por si acaso
    if titulo and re.search(r'indice', titulo, re.IGNORECASE):
        return True
    
    return False


def detectar_notas_huerfanas(ruta_boveda):
    """
    Detecta notas que no tienen ningún enlace hacia otras notas.
    Muestra el título de la nota (primer H1) en lugar del ID numérico.
    """
    
    print(f"🔍 Analizando bóveda: {ruta_boveda}")
    print("-" * 60)
    
    # Patrones
    patron_enlace = r'\[\[([^\|\]]+)(?:\|[^\]]+)?\]\]'  # [[ID]] o [[ID|Alias]]
    patron_titulo = r'^#\s+(.+)$'  # Primer H1: "# Título"
    
    # Estructuras de datos
    archivos_md = {}  # id_nota -> ruta_completa
    enlaces_salientes = defaultdict(set)  # id_nota -> set de ids enlazados
    enlaces_entrantes = defaultdict(set)  # id_nota -> set de ids que lo mencionan
    titulos = {}  # id_nota -> título de la nota

    indices = {}  # id_nota -> True/False
    contador_indices = 0
    indices_huerfanos = []
    indices_sin_salientes = []
    
    # 1. Indexar todos los archivos .md usando GLOB (más robusto para nombres con caracteres especiales)
    print("📂 Indexando archivos con glob...")
    
    # Buscar recursivamente todos los .md
    patron_glob = str(Path(ruta_boveda) / "**/*.md")
    archivos_encontrados = glob.glob(patron_glob, recursive=True)
    
    for archivo in archivos_encontrados:
        ruta_completa = Path(archivo)
        id_nota = ruta_completa.stem  # nombre sin extensión
        archivos_md[id_nota] = ruta_completa
    
    print(f"   ✅ {len(archivos_md)} archivos .md encontrados")

    # Depuración: mostrar TODOS los archivos que podrían ser índices
    print("\n🔍 BÚSQUEDA ESPECÍFICA DE ÍNDICES:")
    indices_encontrados = []
    for id_nota, ruta in archivos_md.items():
        # Buscar patrones de índice en el nombre
        if re.search(r'\d+\.?\s*INDICE', id_nota, re.IGNORECASE):
            indices_encontrados.append(id_nota)
            print(f"   ✅ ÍNDICE DETECTADO: {ruta.name}")
    
    if indices_encontrados:
        print(f"\n📊 Total de índices encontrados por nombre: {len(indices_encontrados)}")
    else:
        print("\n⚠️ No se encontraron índices por nombre. Mostrando archivos que empiezan con número:")
        for id_nota, ruta in list(archivos_md.items())[:20]:
            if id_nota[0].isdigit():
                print(f"   📄 {ruta.name}")
    
    # 2. Procesar cada archivo: extraer título y enlaces
    print("\n📖 Procesando notas...")
    
    for id_nota, ruta in archivos_md.items():
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Extraer título (primer H1)
            match_titulo = re.search(patron_titulo, contenido, re.MULTILINE)
            if match_titulo:
                titulos[id_nota] = match_titulo.group(1).strip()

                # Detectar si es un índice
                if es_nota_indice(id_nota, titulos[id_nota], ruta):
                    indices[id_nota] = True
                    contador_indices += 1
                    print(f"   📌 Procesando ÍNDICE: {ruta.name} -> '{titulos[id_nota]}'")
                else:
                    indices[id_nota] = False
            else:
                # Si no tiene H1, usar el nombre del archivo como fallback
                titulos[id_nota] = f"📄 {ruta.name} (sin título)"
                # Aún así verificar si es índice por nombre
                if es_nota_indice(id_nota, "", ruta):
                    indices[id_nota] = True
                    contador_indices += 1
                    print(f"   📌 Procesando ÍNDICE (solo por nombre): {ruta.name}")
                else:
                    indices[id_nota] = False
            
            # Extraer todos los enlaces
            enlaces = re.findall(patron_enlace, contenido)
            for enlace in enlaces:
                enlace_id = enlace.strip()
                if enlace_id:
                    enlaces_salientes[id_nota].add(enlace_id)
                    enlaces_entrantes[enlace_id].add(id_nota)
                    
        except Exception as e:
            print(f"   ⚠️ Error procesando {ruta.name}: {e}")
            titulos[id_nota] = f"❌ {id_nota} (error al leer)"
    
    # 3. Detectar notas huérfanas
    print("\n🔎 Buscando notas huérfanas...")
    
    notas_huerfanas = []
    notas_con_enlaces = []
    notas_sin_enlaces_pero_mencionadas = []
    
    for id_nota in archivos_md.keys():
        tiene_enlaces_salientes = len(enlaces_salientes[id_nota]) > 0
        tiene_enlaces_entrantes = len(enlaces_entrantes[id_nota]) > 0

        # Clasificar índices específicamente
        if indices.get(id_nota, False):
            if not tiene_enlaces_salientes:
                indices_sin_salientes.append({
                    'id': id_nota,
                    'titulo': titulos.get(id_nota, id_nota),
                    'ruta': archivos_md[id_nota]
                })
                if not tiene_enlaces_entrantes:
                    indices_huerfanos.append({
                        'id': id_nota,
                        'titulo': titulos.get(id_nota, id_nota),
                        'ruta': archivos_md[id_nota]
                    })
                
        if not tiene_enlaces_salientes:
            if not tiene_enlaces_entrantes:
                notas_huerfanas.append({
                    'id': id_nota,
                    'titulo': titulos.get(id_nota, id_nota),
                    'ruta': archivos_md[id_nota]
                })
            else:
                notas_sin_enlaces_pero_mencionadas.append({
                    'id': id_nota,
                    'titulo': titulos.get(id_nota, id_nota),
                    'menciones': len(enlaces_entrantes[id_nota])
                })
        else:
            notas_con_enlaces.append({
                'id': id_nota,
                'titulo': titulos.get(id_nota, id_nota),
                'salientes': len(enlaces_salientes[id_nota]),
                'entrantes': len(enlaces_entrantes[id_nota])
            })
    
    # 4. Mostrar resultados
    print("\n" + "="*60)
    print(f"📊 ESTADÍSTICAS GENERALES")
    print("="*60)
    print(f"📝 Total de notas: {len(archivos_md)}")
    print(f"🔗 Notas con enlaces: {len(notas_con_enlaces)}")
    print(f"📥 Notas mencionadas pero sin enlaces salientes: {len(notas_sin_enlaces_pero_mencionadas)}")
    print(f"🏝️ Notas totalmente huérfanas (sin enlaces): {len(notas_huerfanas)}")
    print(f"\n📌 ESTADÍSTICAS DE ÍNDICES")
    print(f"   📋 Total de índices: {contador_indices}")
    print(f"   🔗 Índices con enlaces: {contador_indices - len(indices_sin_salientes)}")
    print(f"   ⚠️ Índices sin enlaces salientes: {len(indices_sin_salientes)}")
    print(f"   🏝️ Índices totalmente huérfanos: {len(indices_huerfanos)}")
    
    # Mostrar los índices detectados
    if contador_indices > 0:
        print("\n📋 LISTA DE ÍNDICES DETECTADOS:")
        for id_nota, es_indice in indices.items():
            if es_indice:
                print(f"   • {titulos.get(id_nota, id_nota)}")
        
    # 5. Mostrar notas huérfanas (las críticas)
    if notas_huerfanas:
        print("\n" + "="*60)
        print(f"🏝️ NOTAS HUÉRFANAS (sin enlaces de ningún tipo)")
        print("="*60)
        
        # Ordenar por título para facilitar lectura
        notas_huerfanas.sort(key=lambda x: x['titulo'])
        
        for i, nota in enumerate(notas_huerfanas, 1):
            print(f"\n{i}. {nota['titulo']}")
            print(f"   📁 ID: {nota['id']}")
            print(f"   📍 Ruta: {nota['ruta']}")
    else:
        print("\n✅ ¡No hay notas huérfanas! Todas tienen o dan enlaces.")

    # Mostrar indices problemáticos
    if indices_sin_salientes:
        print("\n" + "="*60)
        print(f"📋 ÍNDICES PROBLEMÁTICOS")
        print("="*60)
        
        if indices_huerfanos:
            print("\n🏝️ ÍNDICES TOTALMENTE HUÉRFANOS (sin enlaces de ningún tipo):")
            for idx, indice in enumerate(indices_huerfanos, 1):
                print(f"   {idx}. {indice['titulo']}")
                print(f"      📁 ID: {indice['id']}")
        
        indices_solo_entrantes = [i for i in indices_sin_salientes if i not in indices_huerfanos]
        if indices_solo_entrantes:
            print("\n📥 ÍNDICES QUE SOLO RECIBEN ENLACES (no enlazan a nadie más):")
            for idx, indice in enumerate(indices_solo_entrantes, 1):
                print(f"   {idx}. {indice['titulo']}")
                print(f"      📁 ID: {indice['id']}")
    
    # 6. Mostrar notas que solo reciben enlaces (interesantes)
    if notas_sin_enlaces_pero_mencionadas:
        print("\n" + "="*60)
        print(f"📥 NOTAS QUE SOLO RECIBEN ENLACES (no enlazan a nadie)")
        print("="*60)
        
        # Ordenar por número de menciones (las más importantes primero)
        notas_sin_enlaces_pero_mencionadas.sort(key=lambda x: x['menciones'], reverse=True)
        
        for nota in notas_sin_enlaces_pero_mencionadas[:15]:  # Top 15
            menciones = nota['menciones']
            print(f"📌 {nota['titulo']}")
            print(f"   Recibe {menciones} enlace{'s' if menciones != 1 else ''}")
    
    # 7. Mostrar resumen por carpeta
    print("\n" + "="*60)
    print(f"📁 DISTRIBUCIÓN POR CARPETA")
    print("="*60)
    
    carpetas = defaultdict(lambda: {'total': 0, 'huerfanas': 0})
    for nota in notas_huerfanas:
        ruta = nota['ruta']
        carpeta = ruta.parent.name if ruta.parent.name else 'Raíz'
        carpetas[carpeta]['total'] += 1
        carpetas[carpeta]['huerfanas'] += 1
    
    for nota in notas_con_enlaces:
        ruta = archivos_md[nota['id']]
        carpeta = ruta.parent.name if ruta.parent.name else 'Raíz'
        carpetas[carpeta]['total'] += 1
    
    for carpeta, stats in carpetas.items():
        if stats['total'] > 0:
            porcentaje = (stats['huerfanas'] / stats['total']) * 100
            barra = '█' * int(porcentaje / 5) + '░' * (20 - int(porcentaje / 5))
            print(f"{carpeta:30} [{barra}] {stats['huerfanas']:2d}/{stats['total']:2d} ({porcentaje:.1f}%)")
    
    # 8. Opcional: generar archivo de reporte
    generar_reporte = input("\n💾 ¿Generar archivo de reporte? (s/n): ").lower() == 's'
    
    if generar_reporte:
        name_report = datetime.now().strftime("%Y-%B-%d_%H-%M-%S")
        reporte_path = Path("/home/andres-crow/Obsidian/Reportes Zettelkasten") / (name_report + ".md")
        
        # Asegurar que el directorio existe
        reporte_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(reporte_path, 'w', encoding='utf-8') as f:
            f.write("# Reporte de Notas Huérfanas\n\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            
            f.write("## Resumen\n\n")
            f.write(f"- Total de notas: {len(archivos_md)}\n")
            f.write(f"- Total de índices: {contador_indices}\n")
            f.write(f"- Notas huérfanas: {len(notas_huerfanas)}\n")
            f.write(f"- Índices problemáticos: {len(indices_sin_salientes)}\n\n")
            
            if notas_huerfanas:
                f.write("## Listado de Notas Huérfanas\n\n")
                for nota in notas_huerfanas:
                    f.write(f"### {nota['titulo']}\n")
                    f.write(f"- ID: `{nota['id']}`\n")
                    f.write(f"- Ruta: `{nota['ruta']}`\n\n")
            
            if indices_huerfanos or indices_sin_salientes:
                f.write("\n## Índices Problemáticos\n\n")
                
                if indices_huerfanos:
                    f.write("### Índices Totalmente Huérfanos\n\n")
                    for indice in indices_huerfanos:
                        f.write(f"- **{indice['titulo']}**\n")
                        f.write(f"  - ID: `{indice['id']}`\n")
                        f.write(f"  - Ruta: `{indice['ruta']}`\n\n")
                
                if indices_solo_entrantes:
                    f.write("### Índices que Solo Reciben Enlaces\n\n")
                    for indice in indices_solo_entrantes:
                        f.write(f"- **{indice['titulo']}**\n")
                        f.write(f"  - ID: `{indice['id']}`\n")
                        f.write(f"  - Ruta: `{indice['ruta']}`\n\n")
        
        print(f"✅ Reporte generado: {reporte_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        ruta = "/home/andres-crow/Obsidian"
    
    ruta_boveda = Path(ruta)
    if not ruta_boveda.exists() or not ruta_boveda.is_dir():
        print(f"❌ Error: '{ruta}' no es una carpeta válida")
        sys.exit(1)
    
    detectar_notas_huerfanas(ruta_boveda)