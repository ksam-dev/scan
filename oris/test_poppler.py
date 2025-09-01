# test_poppler.py
import os
import subprocess

def test_poppler():
    # poppler_path = r'C:\poppler\Library\bin'
    poppler_path = r'F:\project\scan_project\poppler-25.07.0\Library\bin'
    
    if poppler_path and os.path.exists(poppler_path):
        env = os.environ.copy()
        env['PATH'] = poppler_path + os.pathsep + env['PATH']
        
        try:
            result = subprocess.run(['pdfinfo', '-v'], 
                                  capture_output=True, text=True, env=env, timeout=10)
            print("Poppler test result:")
            print("Return code:", result.returncode)
            print("Output:", result.stdout)
            print("Error:", result.stderr)
            return result.returncode == 0
        except Exception as e:
            print("Error testing poppler:", e)
            return False
    else:
        print("Poppler path not found")
        return False

if __name__ == "__main__":
    test_poppler()