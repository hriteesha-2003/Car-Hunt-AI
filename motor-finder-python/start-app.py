import uvicorn

import argparse
 
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Start FastAPI app with optional host and port.")

    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address to bind to")

    parser.add_argument("--port", type=int, default=8000, help="Port number to bind to")
 
    args = parser.parse_args()
 
    uvicorn.run("main:app", host=args.host, port=args.port, reload=True)
 