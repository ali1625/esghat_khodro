# scanner_client.py
import pyinsane2
import websockets
import asyncio
import json
from PIL import Image
import io

async def scan_and_send(websocket, path):
    try:
        # دریافت درخواست از مرورگر
        message = await websocket.recv()
        request = json.loads(message)
        if request.get('action') != 'scan':
            await websocket.send(json.dumps({'error': 'Invalid action'}))
            return

        # مقداردهی اولیه اسکنر
        pyinsane2.init()
        devices = pyinsane2.get_devices()
        if not devices:
            await websocket.send(json.dumps({'error': 'No scanner found'}))
            return

        # اسکن با دستگاه اول
        device = devices[0]
        device.options['resolution'].set(300)  # رزولوشن 300 DPI
        scan_session = device.scan(multiple=False)
        image = scan_session.get_img()

        # ذخیره تصویر در حافظه
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=70)  # فشرده‌سازی با کیفیت 70
        img_data = img_byte_arr.getvalue()

        # ارسال تصویر به مرورگر
        await websocket.send(json.dumps({'success': 'Image scanned'}))
        await websocket.send(img_data)  # ارسال باینری تصویر

    except Exception as e:
        await websocket.send(json.dumps({'error': str(e)}))
    finally:
        pyinsane2.exit()

async def main():
    async with websockets.serve(scan_and_send, "localhost", 8001):
        print("Scanner WebSocket server running on ws://localhost:8001")
        await asyncio.Future()  # اجرا به صورت بی‌نهایت

if __name__ == "__main__":
    asyncio.run(main())