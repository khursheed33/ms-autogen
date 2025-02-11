# client.py
import asyncio
import websockets
import json
import aioconsole

async def connect_to_researcher():
    uri = "ws://localhost:8000/ws/research"
    async with websockets.connect(uri) as websocket:
        print("Connected to research server")
        
        # Start research
        topic = input("Enter research topic: ")
        await websocket.send(json.dumps({
            "type": "start_research",
            "topic": topic
        }))
        
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data["type"] == "request_input":
                    print("\nPrompt:", data["prompt"])
                    user_input = await aioconsole.ainput("Your response: ")
                    
                    await websocket.send(json.dumps({
                        "type": "human_input",
                        "input": user_input
                    }))
                    
                elif data["type"] == "input_received":
                    print("Input received by server")
                    
                else:
                    print("\nReceived:", data)
                    
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                break

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(connect_to_researcher())