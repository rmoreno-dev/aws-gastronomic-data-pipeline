# Pipeline de Datos AWS — Cafetería Japonesa

![Python](https://img.shields.io/badge/Python-3.14-blue)
![AWS S3](https://img.shields.io/badge/AWS-S3-orange)
![AWS Glue](https://img.shields.io/badge/AWS-Glue-orange)
![AWS Athena](https://img.shields.io/badge/AWS-Athena-orange)
![Status](https://img.shields.io/badge/Status-Completado-green)

## Planteamiento del problema

Una cafetería "estilo japonesa" ubicada en Concepción, Chile;
necesita centralizar sus datos operacionales del ERP en la nube para 
consultarlos con SQL sin depender de planillas Excel desconectadas.

## Arquitectura del pipeline
ERP (Excel) → Python Extract → S3 Raw
→ S3 Staging (CSV validado)
→ Python Transform
→ S3 Processed (Parquet)
→ AWS Glue Catalog
→ AWS Athena (SQL)

## Stack tecnológico

| Servicio | Uso |
|---|---|
| Python + Pandas | Extracción y transformación |
| AWS S3 | Almacenamiento por capas (raw/staging/processed) |
| AWS Glue | Catálogo de datos |
| AWS Athena | Consultas SQL sobre Parquet |
| Parquet | Formato columnar optimizado |

## Estructura del proyecto

~~~
aws-gastronomic-data-pipeline/
├── src/
│   ├── extract.py         ← validación y carga a S3
│   └── transform.py       ← enriquecimiento y conversión a Parquet
├── sql/
│   └── athena_queries.sql ← 8 queries analíticas documentadas
├── data/
│   ├── raw/               ← datos originales ERP
│   └── processed/         ← datos transformados locales
├── architecture/          ← diagrama de arquitectura AWS
├── requirements.txt
└── README.md
~~~

## Resultados del pipeline

| Métrica | Valor |
|---|---|
| Transacciones procesadas | 10.023 |
| Ítems vendidos | 25.559 |
| Productos únicos | 160 |
| Días de operación | 236 |
| Archivos Parquet en S3 | 4 |
| Costo AWS estimado | ~$0 (Free Tier) |

## Hallazgos clave desde Athena

- **Ingresos totales 2024:** $75,648,488 CLP
- **Ticket promedio:** $7,547 CLP  
- **Método de pago líder:** Débito (63.3%)
- **Franja de mayor ingreso:** Tarde (16–19h)
- **Producto top:** Pan dulce relleno con diseño

## Cómo reproducir

```bash
git clone https://github.com/rmoreno-dev/aws-gastronomic-data-pipeline.git
cd aws-gastronomic-data-pipeline
pip install -r requirements.txt

# Configurar credenciales AWS
aws configure

# Ejecutar pipeline
python src/extract.py
python src/transform.py
```

## Contexto del negocio

Datos reales obtenidos de una cafetería "estilo japonesa" en Concepción, Chile,
con autorización del establecimiento. Datos anonimizados.

## Autor

**Rodolfo Moreno** · Cloud Data Analyst  
[LinkedIn](https://www.linkedin.com/in/rmoreno-dev) · 
[GitHub](https://github.com/rmoreno-dev)