import pandas as pd
import boto3
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


BUCKET   = "gastronomic-pipeline-rmoreno"
REGION   = "us-east-1"
RAW_PATH    = "data/raw/"
TRANS_FILE  = "transacciones_01-01-2024_31-12-2024.xlsx"
CAJA_FILE   = "flujo_caja_26-04-2026.xls"

def validate_excel(filepath: str, sheet: str, engine: str = None) -> pd.DataFrame:
    """Carga y valida un archivo Excel con reglas de negocio gastronómicas."""
    logger.info(f"Cargando {filepath}...")
    kwargs = {"sheet_name": sheet, "header": 1}
    if engine:
        kwargs["engine"] = engine
    df = pd.read_excel(filepath, **kwargs)
    logger.info(f"  Shape raw: {df.shape}")
    return df

def validate_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Valida las reglas de negocio de transacciones."""
    df_raw = df.copy()
    df_raw.columns = [
        'id', 'fecha_ingreso', 'fecha_completado', 'duracion',
        'dia_semana', 'semana', 'operador', 'cliente',
        'correo', 'telefono', 'tipo_venta', 'mesa',
        'total', 'subtotal', 'metodo_pago', 'repartidor',
        'direccion', 'costo_reparto', 'descuento',
        'propina', 'metodo_propina', 'comentario',
        'boleta', 'total_boleta', 'iva', 'medio_venta'
    ]
    df_raw['total'] = pd.to_numeric(df_raw['total'], errors='coerce')
    initial_rows = len(df_raw)
    df_raw = df_raw.dropna(subset=['total'])
    df_raw = df_raw[df_raw['total'] >= 0]
    logger.info(f"  Filas válidas: {len(df_raw)} / {initial_rows}")
    assert len(df_raw) > 0, "No hay transacciones válidas"
    assert (df_raw['total'] >= 0).all(), "Hay totales negativos"
    logger.info("  Validaciones de negocio: OK")
    return df_raw

def validate_items(df: pd.DataFrame) -> pd.DataFrame:
    """Valida las reglas de negocio de ítems vendidos."""
    df_raw = df.copy()
    df_raw.columns = [
        'id', 'fecha_ingreso', 'fecha_completado', 'duracion',
        'dia_semana', 'semana', 'operador', 'cliente',
        'correo', 'telefono', 'tipo_venta', 'producto',
        'seccion', 'comentario_item', 'precio',
        'descuento', 'comentario_pedido'
    ]
    df_raw['precio'] = pd.to_numeric(df_raw['precio'], errors='coerce')
    df_raw = df_raw.dropna(subset=['producto', 'precio'])
    df_raw = df_raw[df_raw['producto'] != 'Ley Redondeo']
    logger.info(f"  Productos únicos: {df_raw['producto'].nunique()}")
    logger.info(f"  Secciones únicas: {df_raw['seccion'].nunique()}")
    return df_raw

def upload_to_s3(local_path: str, s3_key: str) -> bool:
    """Sube un archivo local a S3 con logging."""
    s3 = boto3.client('s3', region_name=REGION)
    try:
        s3.upload_file(local_path, BUCKET, s3_key)
        size = os.path.getsize(local_path) / 1024
        logger.info(f"  Subido: s3://{BUCKET}/{s3_key} ({size:.1f} KB)")
        return True
    except Exception as e:
        logger.error(f"  Error subiendo {s3_key}: {e}")
        return False

def main():
    logger.info("=" * 55)
    logger.info("EXTRACCIÓN Y VALIDACIÓN — PIPELINE GASTRONÓMICO")
    logger.info("=" * 55)

    # Cargar y validar transacciones
    df_trans_raw = validate_excel(
        RAW_PATH + TRANS_FILE,
        sheet="Transacciones"
    )
    df_trans = validate_transactions(df_trans_raw)

    # Cargar y validar ítems
    df_items_raw = validate_excel(
        RAW_PATH + TRANS_FILE,
        sheet="Items"
    )
    df_items = validate_items(df_items_raw)

    # Cargar ítems conteo
    df_conteo_raw = validate_excel(
        RAW_PATH + TRANS_FILE,
        sheet="Items conteo"
    )

    # Cargar flujo de caja
    df_caja_raw = validate_excel(
        RAW_PATH + CAJA_FILE,
        sheet="Item egresos",
        engine="xlrd"
    )

    # Guardar CSVs validados localmente
    logger.info("\nGuardando datos validados localmente...")
    df_trans.to_csv("data/processed/transactions_validated.csv", index=False)
    df_items.to_csv("data/processed/items_validated.csv",        index=False)
    df_conteo_raw.to_csv("data/processed/items_count_raw.csv",   index=False)
    df_caja_raw.to_csv("data/processed/cashflow_raw.csv",        index=False)
    logger.info("  CSVs guardados en data/processed/")

    # Subir archivos raw originales a S3 capa raw
    logger.info("\nSubiendo archivos raw a S3...")
    upload_to_s3(RAW_PATH + TRANS_FILE,
                 f"raw/erp/{TRANS_FILE}")
    upload_to_s3(RAW_PATH + CAJA_FILE,
                 f"raw/erp/{CAJA_FILE}")

    # Subir CSVs validados a S3 capa staging
    logger.info("\nSubiendo staging a S3...")
    upload_to_s3("data/processed/transactions_validated.csv",
                 "staging/transactions/transactions_validated.csv")
    upload_to_s3("data/processed/items_validated.csv",
                 "staging/items/items_validated.csv")
    upload_to_s3("data/processed/items_count_raw.csv",
                 "staging/items_count/items_count_raw.csv")
    upload_to_s3("data/processed/cashflow_raw.csv",
                 "staging/cashflow/cashflow_raw.csv")

    logger.info("\n" + "=" * 55)
    logger.info("EXTRACCIÓN COMPLETADA")
    logger.info(f"  Transacciones validadas: {len(df_trans):,}")
    logger.info(f"  Ítems validados:         {len(df_items):,}")
    logger.info(f"  Bucket S3: s3://{BUCKET}/")
    logger.info("=" * 55)

if __name__ == "__main__":
    main()