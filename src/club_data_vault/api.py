from datetime import date
from io import BytesIO

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from .client import DataClient

app = FastAPI(title="Club Data Vault API", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/v1/exchanges")
def exchanges() -> dict:
    items = DataClient().catalog()
    return {"exchanges": sorted({x["exchange"] for x in items if x.get("exchange")})}


@app.get("/v1/instruments")
def instruments(exchange: str | None = None) -> dict:
    items = DataClient().catalog()
    if exchange:
        items = [x for x in items if x.get("exchange") == exchange]
    return {"instruments": items}


@app.get("/v1/instruments/{instrument_id:path}")
def instrument(instrument_id: str) -> dict:
    item = next((x for x in DataClient().catalog() if x.get("instrument_id") == instrument_id), None)
    if item is None:
        raise HTTPException(404, "Instrument not found")
    return item


@app.get("/v1/market-data")
def market_data(
    instrument: str | None = Query(None),
    exchange: str | None = None,
    symbol: str | None = None,
    interval: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    output_format: str = Query("json", alias="format"),
):
    if output_format not in {"json", "csv", "parquet"}:
        raise HTTPException(400, "format must be json, csv, or parquet")
    try:
        frame = DataClient().load(
            instrument=instrument, exchange=exchange, symbol=symbol,
            interval=interval, start_date=start_date, end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "Unable to read dataset") from exc
    if output_format == "json":
        return {"data": frame.astype({"timestamp": "str"}).to_dict(orient="records")}
    if output_format == "csv":
        return Response(frame.to_csv(index=False), media_type="text/csv")
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False)
    return Response(buffer.getvalue(), media_type="application/vnd.apache.parquet")
