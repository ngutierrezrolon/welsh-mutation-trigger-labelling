import subprocess
import sys
import shutil
import os
from tqdm import tqdm

class parser:
    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.project_dir = os.path.join(self.BASE_DIR, "CyTag")
        self.input_folder = os.path.join(self.project_dir, "txt")
        self.input_file = os.path.join(self.input_folder, "input_text.txt")
        self.output_folder = os.path.join(self.project_dir, "allbwn", "cytag")
        self.app_path = os.path.join(self.project_dir, "app.py")
        self.output_file = os.path.join(self.output_folder, "canlyniad.tsv")
        self.readings_file = os.path.join(self.output_folder, "darlleniadauWediCG.txt")
    
    def run_cytag(self, text):
        
        # Writes text to 'input_text.txt' , runs CyTag2, and reads output

        #os.makedirs(self.input_folder, exist_ok=True)
        with open(self.input_file, "w", encoding="utf-8") as f:
            f.write(text)
            
      

        # Run CyTag2
        try:
            python_executable = sys.executable
            result = subprocess.run(
                [python_executable, self.app_path, "-c"],  
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Error running CyTag2: {e}")
            print("Standard Output:", e.stdout)
            print("Standard Error:", e.stderr)
            return None

        if not os.path.exists(self.output_file):
            print(f"Error: {self.output_file} not found!")
            return None
 

        # Read and process the output file
        # rows = []
        # with open(self.output_file, "r", encoding="utf-8") as POS_output:
        #     for line in POS_output:
        #     #for line in tqdm(POS_output, desc="Reading file"):
        #         #print(line)
        #         line = line.strip()
        #         sections = line.split("\t")

        #         if len(sections) > 6: 
        #             wordform = sections[1]
        #             #token_counter[wordform] += 1
                    
        #             #sent_id = sections[2]
        #             lemma = sections[3]
        #             #print(lemma)
        #             simple_tag = sections[5]
        #             pos_tag = sections[6]
        #             mut_tag = sections[7]
        #             rows.append({
        #             "wordform": wordform,
        #             "lemma": lemma,
        #             "simple_tag": simple_tag,
        #             "pos_tag": pos_tag,
        #             "mut_tag": mut_tag
        #         })
        # df = pd.DataFrame(rows)
        # return df

        return self.readings_file, self.output_file

    def cg_output(self, cg_readings):
        """ Given a set of CG-formatted readings, run VISL CG-3 """
        vislcg3_location = shutil.which("vislcg3")
        grammar_path = os.path.join(self.project_dir, "postagger", "grammar", "trigger.cg")

        cg_process = subprocess.Popen(
            [vislcg3_location, '--soft-limit', '45', '--hard-limit', "100", "-B", "-v", '0', '-g', grammar_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        cg_output, cg_error = cg_process.communicate(input=cg_readings.encode("utf-8"))
        if b"Grammar could not be parsed" in cg_error:
            err_msg = cg_error.decode("utf-8")
            msg = colored("There is a problem with the constraint grammar!\nPlease fix before rerunning the code.", attrs=['reverse', 'bold'])
            out_msg = "\n\n{}\n\n{}".format(msg, err_msg)
            raise RuntimeError(out_msg)
        else:
            return cg_output.decode("utf-8")

    def get_output(self, text):
        readings_path, output_path = self.run_cytag(text)
        if readings_path:
            with open(readings_path, "r", encoding="utf-8") as f:
                cg_input = f.read()
            cg_out = self.cg_output(cg_input)
            return cg_out
        else:
            return "CyTag failed; no readings to process."
    