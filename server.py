import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import MetaTrader5 as mt5

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    if not mt5.initialize():
        print("❌ MT5 Initialization failed")
    else:
        print("✅ MT5 Initialized successfully")

@app.get("/api/data")
def get_historical_data(symbol: str = "XAUUSD", timeframe: str = "M15", count: int = 30):
    TF_MAP = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30, "1H": mt5.TIMEFRAME_H1, "4H": mt5.TIMEFRAME_H4, "1D": mt5.TIMEFRAME_D1}
    tf = TF_MAP.get(timeframe.upper(), mt5.TIMEFRAME_M15)
    
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is not None and len(rates) > 0:
        history = [{"time": int(r[0]), "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": int(r[5])} for r in rates]
        return {"status": "success", "data": history}
    return {"status": "error", "message": "ไม่สามารถดึงข้อมูลจาก MT5 ได้"}

# -------------------------------------------------------------
# ระบบ WebSocket สื่อสาร 2 ทาง (เปลี่ยนกราฟลื่นไหล ไม่หลุดเชื่อมต่อ)
# -------------------------------------------------------------
@app.websocket("/ws/chart")
async def chart_endpoint(websocket: WebSocket, symbol: str = "XAUUSD", timeframe: str = "M15"):
    await websocket.accept()
    print(f"💻 uBlue Client Connected! Initial: {symbol} | {timeframe}")
    
    TF_MAP = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30, "1H": mt5.TIMEFRAME_H1, "4H": mt5.TIMEFRAME_H4, "1D": mt5.TIMEFRAME_D1}
    
    current_symbol = symbol
    current_tf = TF_MAP.get(timeframe.upper(), mt5.TIMEFRAME_M15)
    mt5.symbol_select(current_symbol, True)

    async def send_history():
        rates = mt5.copy_rates_from_pos(current_symbol, current_tf, 0, 150)
        if rates is not None and len(rates) > 0:
            history = [{"time": int(r[0]), "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": int(r[5])} for r in rates]
            await websocket.send_json({"type": "history", "data": history})

    # ส่งข้อมูลชุดแรกทันทีที่เชื่อมต่อ
    await send_history()

    # Task สำหรับรอรับ "คำสั่ง (Command)" จาก Mac
    async def listen_commands():
        nonlocal current_symbol, current_tf
        try:
            while True:
                msg = await websocket.receive_json()
                if msg.get("action") == "change_tf":
                    current_tf = TF_MAP.get(msg.get("tf", "M15").upper(), mt5.TIMEFRAME_M15)
                    print(f"🔄 เปลี่ยน Timeframe เป็น {msg.get('tf')} โดยไม่ตัดสาย")
                    await send_history()
                elif msg.get("action") == "change_symbol":
                    current_symbol = msg.get("symbol")
                    mt5.symbol_select(current_symbol, True)
                    print(f"🔄 เปลี่ยนคู่เงินเป็น {current_symbol} โดยไม่ตัดสาย")
                    await send_history()
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"Listen Error: {e}")

    # รัน Task รอรับคำสั่งคู่ขนานไปกับการส่งแท่งเทียนปัจจุบัน
    listen_task = asyncio.create_task(listen_commands())

    try:
        while True:
            # ถ้า Client ตัดสายไปแล้ว ให้ออกจาก Loop
            if listen_task.done():
                break
            
            live_rates = mt5.copy_rates_from_pos(current_symbol, current_tf, 0, 1)
            if live_rates is not None and len(live_rates) > 0:
                r = live_rates[0]
                current_candle = {"time": int(r[0]), "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": int(r[5])}
                await websocket.send_json({"type": "tick", "data": current_candle})
            
            await asyncio.sleep(1) # อัปเดตแท่งเทียนทุก 1 วินาที
            
    except WebSocketDisconnect:
        print("🔌 Client Disconnected")
    except Exception as e:
        print(f"⚠️ Socket Error: {e}")
    finally:
        listen_task.cancel()

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting uBlue Server on Port 5001...")
    uvicorn.run(app, host="0.0.0.0", port=5001)