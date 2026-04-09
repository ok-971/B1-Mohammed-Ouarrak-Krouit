#!/usr/bin/env python3
"""
Autoevaluación local de prácticas - VERSIÓN DEFINITIVA
- Autoevaluacion.md: ÚLTIMA evaluación (vista rápida)
- HistoricoAutoevaluaciones.md: TODO el histórico completo
"""

import subprocess
import re
import hashlib
from datetime import datetime
from pathlib import Path

# Archivos
AUTOEVALUACION = 'Autoevaluacion.md'
HISTORICO = 'HistoricoAutoevaluaciones.md'
TEST_DIR = 'test'

# Pesos sistema ponderado
PESO_MIN, PESO_PRES, PESO_NPRES = 0.4, 0.4, 0.2


def obtener_nombre_repo():
    """Obtiene el nombre del repositorio desde git"""
    try:
        result = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            match = re.search(r'/([^/]+)\.git$', url) or re.search(r':([^:]+)\.git$', url)
            if match:
                return match.group(1)
    except:
        pass
    return Path.cwd().name


def generar_hash_codigo():
    """Genera hash SHA-256 de todos los archivos .py en carpetas PR*"""
    archivos = []
    
    for carpeta in sorted(Path('.').glob('PR*/')):
        if carpeta.is_dir():
            for archivo in sorted(carpeta.rglob('*.py')):
                try:
                    with open(archivo, 'rb') as f:
                        contenido = f.read()
                        hash_archivo = hashlib.sha256(contenido).hexdigest()
                        archivos.append({
                            'path': str(archivo),
                            'hash': hash_archivo,
                            'size': len(contenido)
                        })
                except:
                    pass
    
    if not archivos:
        return "VACIO", []
    
    contenido_global = ''.join(f"{a['path']}:{a['hash']}" for a in archivos)
    hash_global = hashlib.sha256(contenido_global.encode()).hexdigest()
    
    return hash_global, archivos


def ejecutar_pytest():
    """Ejecuta pytest en carpeta /test"""
    print("🧪 Ejecutando pruebas...")
    try:
        result = subprocess.run(
            ['pytest', '--tb=short', '--disable-warnings', TEST_DIR],
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.stdout + result.stderr
    except Exception as e:
        print(f"❌ Error al ejecutar pytest: {e}")
        return ""


def procesar_resultados(output):
    """Extrae resultados de pytest"""
    resultados = {}
    patron = re.compile(r'^([a-zA-Z0-9_./-]+\.py)\s+(.+)$', re.MULTILINE)
    
    for match in patron.finditer(output):
        archivo = match.group(1).replace('test/', '')
        simbolos = match.group(2).strip()
        resultado = (simbolos
            .replace('.', ':heavy_check_mark:')
            .replace('F', ':x:')
            .replace('s', ':construction:')
            .replace('E', ':heavy_exclamation_mark:'))
        resultados[archivo] = resultado
    
    return resultados


def calcular_porcentaje(resultado):
    """Calcula % de tests pasados"""
    if not resultado:
        return -1
    ok = resultado.count(':heavy_check_mark:')
    fail = resultado.count(':x:')
    skip = resultado.count(':construction:')
    total = ok + fail + skip
    return (ok * 100 // total) if total > 0 else -1


def contar_tests(resultado):
    """Cuenta tests pasados y totales"""
    if not resultado:
        return (0, 0)
    ok = resultado.count(':heavy_check_mark:')
    fail = resultado.count(':x:')
    skip = resultado.count(':construction:')
    return (ok, ok + fail + skip)


def calcular_practica(min_pct, pres_pct, npres_pct):
    """Calcula nota ponderada (MIN=40%, PRES=40%, NPRES=20%)"""
    if min_pct == -1 or pres_pct == -1:
        return -1
    nota = min_pct * PESO_MIN + pres_pct * PESO_PRES
    if npres_pct != -1:
        nota += npres_pct * PESO_NPRES
    return int(nota)


def generar_tabla_resultados(resultados):
    """Genera tabla markdown de resultados detallados"""
    if not resultados:
        return "No hay resultados.\n"
    
    tabla = "| Archivo | % Superado | Resultado |\n"
    tabla += "|---|:---:|---:|\n"
    
    for archivo in sorted(resultados.keys()):
        porcentaje = calcular_porcentaje(resultados[archivo])
        pasados, totales = contar_tests(resultados[archivo])
        
        if porcentaje == -1:
            pct_str = "-"
        else:
            pct_str = f"**{porcentaje}%** ({pasados}/{totales})"
        
        tabla += f"| {archivo} | {pct_str} | {resultados[archivo]} |\n"
    
    return tabla


def extraer_username(nombre_repo):
    """
    Extrae el username del nombre del repositorio.
    Soporta formatos:
      - E-repo-jgarcia        -> jgarcia
      - b-2026-jgarcia-ual    -> jgarcia-ual
      - a-2026-jgarcia-ual    -> jgarcia-ual
    Fallback: intenta obtenerlo de git config user.name
    """
    # Formato E-repo-{username}
    if nombre_repo.startswith('E-repo-'):
        return nombre_repo.replace('E-repo-', '')

    # Formato {grupo}-{año}-{username}  (ej: b-2026-jgarcia-ual)
    partes = nombre_repo.split('-')
    if len(partes) >= 3 and partes[1].isdigit() and len(partes[1]) == 4:
        # Elimina grupo (partes[0]) y año (partes[1]), el resto es el username
        return '-'.join(partes[2:])

    # Fallback: intentar git config user.name
    try:
        result = subprocess.run(
            ['git', 'config', '--get', 'user.name'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass

    return nombre_repo


def generar_resumen(resultados, nombre_repo):
    """Genera tabla resumen con notas ponderadas"""
    username = extraer_username(nombre_repo)

    def pct(nombre):
        return calcular_porcentaje(resultados.get(nombre, ''))

    # PR0, PR2, PR6 tienen un único archivo de test sin sufijos MIN/PRES/NPRES
    p0 = pct('test_pr0.py')
    p2 = pct('test_pr2.py')
    p6 = pct('test_pr6.py')

    # PR3 también tiene un único archivo (sin MIN/PRES/NPRES)
    p3 = pct('test_pr3.py')

    # PR1, PR4, PR5, PR7, PR8 tienen tres archivos MIN/PRES/NPRES
    p1 = calcular_practica(pct('test_pr1_MIN.py'), pct('test_pr1_PRES.py'), pct('test_pr1_NPRES.py'))
    p4 = calcular_practica(pct('test_pr4_MIN.py'), pct('test_pr4_PRES.py'), pct('test_pr4_NPRES.py'))
    p5 = calcular_practica(pct('test_pr5_MIN.py'), pct('test_pr5_PRES.py'), pct('test_pr5_NPRES.py'))
    p7 = calcular_practica(pct('test_pr7_MIN.py'), pct('test_pr7_PRES.py'), pct('test_pr7_NPRES.py'))
    p8 = calcular_practica(pct('test_pr8_MIN.py'), pct('test_pr8_PRES.py'), pct('test_pr8_NPRES.py'))
    
    fmt = lambda v: f"{v}%" if v != -1 else "-"
    notas = [p0, p1, p2, p3, p4, p5, p6, p7, p8]
    validas = [n for n in notas if n != -1]
    nota_final = f"{sum(validas) // len(validas)}%" if validas else "-"
    
    resumen = "| | PR0 | PR1 | PR2 | PR3 | PR4 | PR5 | PR6 | PR7 | PR8 | **NOTA** |\n"
    resumen += "|---|-----|-----|-----|-----|-----|-----|-----|-----|-----|----------|\n"
    resumen += f"| {username} | {fmt(p0)} | {fmt(p1)} | {fmt(p2)} | {fmt(p3)} | {fmt(p4)} | {fmt(p5)} | {fmt(p6)} | {fmt(p7)} | {fmt(p8)} | **{nota_final}** |\n"
    
    return resumen, nota_final, username


def generar_estadisticas(resultados, nota_final):
    """Genera estadísticas globales del repositorio"""
    total_pasados = 0
    total_tests = 0
    
    for resultado in resultados.values():
        pasados, totales = contar_tests(resultado)
        total_pasados += pasados
        total_tests += totales
    
    if total_tests == 0:
        pct_tests = "0%"
    else:
        pct_tests = f"{(total_pasados * 100) // total_tests}%"
    
    estadisticas = "\n**📊 Estadísticas:**\n"
    estadisticas += f"- **Tests pasados:** {pct_tests} ({total_pasados}/{total_tests} tests ejecutados)\n"
    estadisticas += f"- **Calificación ponderada:** {nota_final}\n"
    
    return estadisticas


def actualizar_autoevaluacion_ultima(nombre_repo, username, tabla, resumen, estadisticas, hash_codigo, archivos):
    """
    SOBRESCRIBE Autoevaluacion.md con la ÚLTIMA evaluación
    Vista rápida para el estudiante
    """
    fecha_eval = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    timestamp_iso = datetime.now().isoformat()
    
    contenido_completo = f"""# 🎓 Autoevaluación Local (Última ejecución)

Este archivo muestra el resultado de tu última prueba. El historial completo está en `HistoricoAutoevaluaciones.md`.

**Sistema de calificación:** MIN=40%, PRES=40%, NPRES=20% (opcional)

---

## 📝 Repositorio: **{nombre_repo}**

**Fecha de evaluación:** {fecha_eval}

### 📊 Resumen Ponderado

**Sistema:** MIN=40%, PRES=40%, NPRES=20%

{resumen}
### 📋 Detalle de Tests

{tabla}
{estadisticas}

### 🔐 Verificación de integridad

- **Hash de código:** `{hash_codigo}`
- **Archivos verificados:** {len(archivos)} archivos Python
- **Timestamp ISO:** `{timestamp_iso}`
- **Usuario:** `{username}`
"""
    
    with open(AUTOEVALUACION, 'w', encoding='utf-8') as f:
        f.write(contenido_completo)
    
    print(f"✅ {AUTOEVALUACION} actualizado (última evaluación)")


def actualizar_historico_completo(nombre_repo, username, tabla, resumen, estadisticas, hash_codigo, archivos):
    """
    AÑADE al HistoricoAutoevaluaciones.md el histórico completo
    Con toda la información de cada evaluación
    """
    fecha_eval = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    timestamp_iso = datetime.now().isoformat()
    
    # Crear NUEVA evaluación completa
    nueva_evaluacion = f"""
---

## Evaluación: {fecha_eval}
## 📝 Repositorio: **{nombre_repo}**

**Fecha de evaluación:** {fecha_eval}

### 📊 Resumen Ponderado

{resumen}
### 📋 Detalle de Tests

{tabla}
{estadisticas}

### 🔐 Verificación de integridad

- **Hash de código:** `{hash_codigo}`
- **Archivos verificados:** {len(archivos)} archivos Python
- **Timestamp ISO:** `{timestamp_iso}`
- **Usuario:** `{username}`
"""
    
    # Leer contenido existente
    try:
        with open(HISTORICO, 'r', encoding='utf-8') as f:
            contenido_existente = f.read()
    except FileNotFoundError:
        contenido_existente = """# 📚 Histórico de Autoevaluaciones

Registro cronológico de TODAS las evaluaciones.

---
"""
    
    # AÑADIR al final (orden cronológico)
    with open(HISTORICO, 'w', encoding='utf-8') as f:
        f.write(contenido_existente + nueva_evaluacion)
    
    print(f"✅ {HISTORICO} actualizado (evaluación añadida al histórico)")


def main():
    print("=" * 60)
    print("🎓 AUTOEVALUACIÓN LOCAL DEFINITIVA")
    print("=" * 60)
    
    nombre_repo = obtener_nombre_repo()
    print(f"📦 Repositorio: {nombre_repo}\n")
    
    # Generar hash de código ANTES de ejecutar tests
    print("🔐 Generando hash de verificación...")
    hash_codigo, archivos = generar_hash_codigo()
    print(f"   Hash: {hash_codigo[:32]}...")
    print(f"   Archivos verificados: {len(archivos)}\n")
    
    if not Path(TEST_DIR).exists():
        print(f"❌ No existe la carpeta /{TEST_DIR}")
        return 1
    
    output = ejecutar_pytest()
    if not output:
        return 1
    
    resultados = procesar_resultados(output)
    if not resultados:
        print("⚠️  No se encontraron resultados")
        return 1
    
    tabla = generar_tabla_resultados(resultados)
    resumen, nota_final, username = generar_resumen(resultados, nombre_repo)
    estadisticas = generar_estadisticas(resultados, nota_final)
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN:")
    print("=" * 60)
    print(resumen)
    print(estadisticas)
    
    print("\n" + "=" * 60)
    # Actualizar AMBOS archivos
    actualizar_autoevaluacion_ultima(nombre_repo, username, tabla, resumen, estadisticas, hash_codigo, archivos)
    actualizar_historico_completo(nombre_repo, username, tabla, resumen, estadisticas, hash_codigo, archivos)
    
    print("=" * 60)
    print("✅ ¡Listo! Archivos actualizados con verificación anti-fraude")
    print("   - Autoevaluacion.md: Última evaluación")
    print("   - HistoricoAutoevaluaciones.md: Histórico completo")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    exit(main())
