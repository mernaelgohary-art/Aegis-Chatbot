import time
from ollama import Client
# This assumes db_manager.py is in the same folder
from db_manager import save_chat_message 

client = Client(host='http://127.0.0.1:11434')

# Updated list to include Llama 3
MODELS = [
    "xploiter:latest",
    "qwen2.5-coder:7b",
    "mistral:latest",
    "soc-bot:latest",
    "llama3:latest"
]

PROMPT = """
Analyze the following scenario for the AEGIS platform:
An rsyslog entry shows multiple failed SSH login attempts from an internal IP followed by a successful 'sudo' command.
1. Identify the specific attack pattern.
2. Provide a 3-step mitigation strategy using Linux commands.
"""

def run_benchmark():
    print(f"--- Starting AEGIS R&D Benchmark ---")
    
    for model in MODELS:
        print(f"Testing {model}...", end=" ", flush=True)
        start_time = time.time()
        
        try:
            # 1. Get response from Ollama
            response = client.chat(model=model, messages=[
                {'role': 'system', 'content': 'You are a Senior SOC Analyst.'},
                {'role': 'user', 'content': PROMPT}
            ])
            
            duration = round(time.time() - start_time, 2)
            answer = response['message']['content']
            
            # 2. Save results to the Database
            # We create a session ID based on the model name
            session_id = f"benchmark-{model}"
            
            # Save to PostgreSQL
            save_chat_message(session_id, {
                "role": "assistant", 
                "content": answer, 
                "duration_seconds": duration,
                "prompt": PROMPT
            })
            
            # 3. Save results to text files (as a backup)
            safe_filename = model.replace("/", "_").replace(":", "_")
            with open(f"{safe_filename}_analysis.txt", "w", encoding="utf-8") as f:
                f.write(f"Model: {model}\nDuration: {duration}s\n")
                f.write("-" * 30 + "\n")
                f.write(answer)
                
            print(f"Done! ({duration}s) -> Saved to DB and File.")
            
        except Exception as e:
            print(f"\nFAILED to process {model}. Error: {str(e)}")

if __name__ == "__main__":
    run_benchmark()