import os

def create_llm_dump(library_path, output_file):
    with open(output_file, "w", encoding="utf-8") as outfile:
        # Walk through the directory
        for root, dirs, files in os.walk(library_path):
            # Skip common junk folders
            if '__pycache__' in dirs: dirs.remove('__pycache__')
            if '.git' in dirs: dirs.remove('.git')
            
            for file in files:

                if "_pb2" in file: continue          # Skip massive machine-generated Google files
                if "test" in file.lower(): continue  # Skip test files
                if "gapic" in file.lower(): continue # Skip low-level connection code (optional)
                
                # Only grab python files (you can add .md or .txt if needed)
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, library_path)
                    
                    # WRITE THE HEADER
                    outfile.write(f"\n{'='*20}\n")
                    outfile.write(f"FILE: {rel_path}\n")
                    outfile.write(f"{'='*20}\n\n")
                    
                    # WRITE THE CODE
                    try:
                        with open(full_path, "r", encoding="utf-8") as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"# Error reading file: {e}")
                    
                    outfile.write("\n")
    
    print(f"Success! Library dumped to: {output_file}")

# --- USAGE ---
# Replace 'path_to_library' with the folder of the library you want to copy
# Example: create_llm_dump("C:/Python39/Lib/site-packages/requests", "requests_context.txt")

# If you don't know the path, run this import trick first:
#import google.genai
# print(f"Library is at: {os.path.dirname(google.genai.__file__)}")
# Then copy that path below:
# create_llm_dump(os.path.dirname(google.genai.__file__), "library_dump.txt")

create_llm_dump("C:\\Users\\User\\Documents\\NOVAIMS\\Ano-3\\CapstoneProject\\CProject_2_epoch\\ai_course_env\\lib\\site-packages\\google\\genai", "genai_dump.txt")