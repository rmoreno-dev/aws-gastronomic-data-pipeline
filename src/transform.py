import pandas as pd
import numpy as np
import boto3
import io
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BUCKET = "gastronomic-pipeline-rmoreno"
REGION = "us-east-1"


def read_csv_from_s3(s3_key: str) -> pd.DataFrame:
    s3 = boto3.client('s3', region_name=REGION)
    obj = s3.get_object(Bucket=BUCKET, Key=s3_key)
    df = pd.read_csv(io.BytesIO(obj['Body'].read()))
    logger.info(f"  Leído desde S3: {s3_key} — {df.shape}")
    return df


def upload_parquet_to_s3(df: pd.DataFrame, s3_key: str) -> None:
    s3 = boto3.client('s3', region_name=REGION)
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine='pyarrow')
    buffer.seek(0)
    s3.put_object(Bucket=BUCKET, Key=s3_key, Body=buffer.getvalue())
    size_kb = buffer.getbuffer().nbytes / 1024
    logger.info(f"  Subido Parquet: s3://{BUCKET}/{s3_key} ({size_kb:.1f} KB)")


def transform_transactions(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando transacciones...")
    df = df.copy()

    df['fecha'] = pd.to_datetime(
        df['fecha_ingreso'].str.extract(r'(\d{2}/\d{2}/\d{4})')[0],
        format='%d/%m/%Y'
    )
    df['hora'] = pd.to_datetime(
        df['fecha_ingreso'].str.extract(r'(\d{2}:\d{2})')[0],
        format='%H:%M'
    ).dt.hour

    df['year']       = df['fecha'].dt.year
    df['month']      = df['fecha'].dt.month
    df['month_name'] = df['fecha'].dt.strftime('%B')
    df['day_of_week'] = df['fecha'].dt.day_name()
    df['is_weekend'] = df['fecha'].dt.dayofweek >= 5
    df['week']       = df['fecha'].dt.isocalendar().week.astype(int)

    def franja(h):
        if h < 10:   return 'apertura'
        elif h < 13: return 'manana'
        elif h < 16: return 'almuerzo'
        elif h < 19: return 'tarde'
        else:        return 'cierre'

    df['franja_horaria'] = df['hora'].apply(franja)

    df['total']    = pd.to_numeric(df['total'],    errors='coerce').fillna(0)
    df['descuento'] = pd.to_numeric(df['descuento'], errors='coerce').fillna(0)
    df['iva']      = pd.to_numeric(df['iva'],      errors='coerce').fillna(0)
    df['propina']  = pd.to_numeric(df['propina'],  errors='coerce').fillna(0)

    def simplificar_pago(m):
        m = str(m)
        if 'Débito'        in m: return 'Debito'
        if 'Efectivo'      in m: return 'Efectivo'
        if 'Crédito'       in m: return 'Credito'
        if 'Transferencia' in m: return 'Transferencia'
        if 'Edenred'       in m: return 'Edenred'
        if 'Sodexo'        in m: return 'Sodexo'
        return 'Otro'

    df['metodo_pago_clean'] = df['metodo_pago'].apply(simplificar_pago)

    cols = [
        'id', 'fecha', 'year', 'month', 'month_name',
        'day_of_week', 'is_weekend', 'week', 'hora',
        'franja_horaria', 'tipo_venta', 'metodo_pago_clean',
        'total', 'descuento', 'iva', 'propina'
    ]
    df_final = df[cols].copy()
    logger.info(f"  Transacciones transformadas: {len(df_final):,} filas")
    return df_final


def transform_items(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando ítems...")
    df = df.copy()

    df['fecha'] = pd.to_datetime(
        df['fecha_ingreso'].str.extract(r'(\d{2}/\d{2}/\d{4})')[0],
        format='%d/%m/%Y'
    )
    df['hora'] = pd.to_datetime(
        df['fecha_ingreso'].str.extract(r'(\d{2}:\d{2})')[0],
        format='%H:%M'
    ).dt.hour

    df['year']       = df['fecha'].dt.year
    df['month']      = df['fecha'].dt.month
    df['day_of_week'] = df['fecha'].dt.day_name()
    df['is_weekend'] = df['fecha'].dt.dayofweek >= 5

    df['precio']    = pd.to_numeric(df['precio'],    errors='coerce').fillna(0)
    df['descuento'] = pd.to_numeric(df['descuento'], errors='coerce').fillna(0)
    df['revenue']   = df['precio'] - df['descuento']

    df['producto'] = df['producto'].str.strip()
    df['seccion']  = df['seccion'].str.strip()
    df = df[df['producto'] != 'Ley Redondeo']

    cols = [
        'id', 'fecha', 'year', 'month', 'day_of_week',
        'is_weekend', 'hora', 'tipo_venta', 'producto',
        'seccion', 'precio', 'descuento', 'revenue'
    ]
    df_final = df[cols].copy()
    logger.info(f"  Ítems transformados: {len(df_final):,} filas")
    return df_final


def create_product_summary(df_items: pd.DataFrame) -> pd.DataFrame:
    logger.info("Creando resumen de productos...")
    summary = df_items.groupby(['producto', 'seccion']).agg(
        cantidad=('producto', 'count'),
        ingresos_totales=('revenue', 'sum'),
        precio_promedio=('precio', 'mean'),
        n_transacciones=('id', 'nunique')
    ).reset_index()

    total_unidades = summary['cantidad'].sum()
    summary['menu_mix_pct'] = (
        summary['cantidad'] / total_unidades * 100
    ).round(3)

    n_items   = len(summary)
    umbral_mm = 70 / n_items
    umbral_mc = summary['precio_promedio'].mean()

    def clasificar(row):
        alta_pop  = row['menu_mix_pct']    >= umbral_mm
        alto_marg = row['precio_promedio'] >= umbral_mc
        if alta_pop and alto_marg: return 'Estrella'
        if alta_pop:               return 'Caballo de Trabajo'
        if alto_marg:              return 'Interrogante'
        return 'Perro'

    summary['clasificacion_menu'] = summary.apply(clasificar, axis=1)
    summary = summary.sort_values('ingresos_totales', ascending=False)

    logger.info(f"  Productos únicos: {len(summary)}")
    logger.info(f"  Estrellas:  {(summary['clasificacion_menu']=='Estrella').sum()}")
    logger.info(f"  Caballos:   {(summary['clasificacion_menu']=='Caballo de Trabajo').sum()}")
    logger.info(f"  Interrogantes: {(summary['clasificacion_menu']=='Interrogante').sum()}")
    logger.info(f"  Perros:     {(summary['clasificacion_menu']=='Perro').sum()}")
    return summary


def create_daily_summary(df_trans: pd.DataFrame) -> pd.DataFrame:
    logger.info("Creando resumen diario...")
    daily = df_trans.groupby(
        ['fecha', 'year', 'month', 'day_of_week', 'is_weekend']
    ).agg(
        ingresos=('total', 'sum'),
        transacciones=('id', 'count'),
        ticket_promedio=('total', 'mean'),
        descuentos=('descuento', 'sum'),
        propinas=('propina', 'sum')
    ).reset_index()
    daily = daily.sort_values('fecha')
    logger.info(f"  Días únicos: {len(daily)}")
    return daily


def main():
    logger.info("=" * 55)
    logger.info("TRANSFORMACIÓN — PIPELINE GASTRONÓMICO")
    logger.info("=" * 55)

    df_trans = read_csv_from_s3(
        "staging/transactions/transactions_validated.csv")
    df_items = read_csv_from_s3(
        "staging/items/items_validated.csv")

    df_trans_clean  = transform_transactions(df_trans)
    df_items_clean  = transform_items(df_items)
    df_product_summ = create_product_summary(df_items_clean)
    df_daily_summ   = create_daily_summary(df_trans_clean)

    logger.info("\nSubiendo capa processed a S3...")
    upload_parquet_to_s3(
        df_trans_clean,
        "processed/transactions/transactions_clean.parquet")
    upload_parquet_to_s3(
        df_items_clean,
        "processed/items/items_clean.parquet")
    upload_parquet_to_s3(
        df_product_summ,
        "processed/products/product_summary.parquet")
    upload_parquet_to_s3(
        df_daily_summ,
        "processed/daily/daily_summary.parquet")

    df_trans_clean.to_csv(
        "data/processed/transactions_clean.csv",  index=False)
    df_items_clean.to_csv(
        "data/processed/items_clean.csv",          index=False)
    df_product_summ.to_csv(
        "data/processed/product_summary.csv",      index=False)
    df_daily_summ.to_csv(
        "data/processed/daily_summary.csv",        index=False)

    logger.info("\n" + "=" * 55)
    logger.info("TRANSFORMACIÓN COMPLETADA")
    logger.info(f"  Transacciones procesadas: {len(df_trans_clean):,}")
    logger.info(f"  Ítems procesados:         {len(df_items_clean):,}")
    logger.info(f"  Productos únicos:         {len(df_product_summ):,}")
    logger.info(f"  Días de operación:        {len(df_daily_summ):,}")
    logger.info("  Archivos Parquet en s3://processed/")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()