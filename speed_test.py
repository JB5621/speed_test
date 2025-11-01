import speedtest
import time
import sys

def simple_loader(duration=3, message="Loading"):
    """Simple loading animation without external dependencies"""
    animation = ["[■□□□□□□□□□]","[■■□□□□□□□□]", "[■■■□□□□□□□]", "[■■■■□□□□□□]", "[■■■■■□□□□□]",
                "[■■■■■■□□□□]", "[■■■■■■■□□□]", "[■■■■■■■■□□]", "[■■■■■■■■■□]", "[■■■■■■■■■■]"]
    
    start_time = time.time()
    i = 0
    
    while time.time() - start_time < duration:
        sys.stdout.write(f"\r{message} {animation[i % len(animation)]}")
        sys.stdout.flush()
        time.sleep(0.2)
        i += 1
    
    sys.stdout.write(f"\r{message} [COMPLETED]    \n")

def basic_speed_test():
    print("🌐 Starting Speed Test")
    print("=" * 40)
    
    try:
        simple_loader(2, "Initializing")
        st = speedtest.Speedtest()
        
        simple_loader(2, "Finding server")
        st.get_best_server()
        
        simple_loader(3, "Download test")
        download = st.download() / 1000000
        
        simple_loader(2, "Upload test")
        upload = st.upload() / 1000000
        
        ping = st.results.ping
        
        print("\n" + "✅ RESULTS " + "="*30)
        print(f"⬇️  Download: {download:.2f} Mbps")
        print(f"⬆️  Upload:   {upload:.2f} Mbps")
        print(f"🏓 Ping:     {ping:.2f} ms")
        print("=" * 40)
        
    except Exception as e:
        print(f"\r❌ Error: {e}")

if __name__ == "__main__":
    basic_speed_test()