"""
Project Entry Point
"""

import os
import subprocess


def run_dashboard():

    os.system(
        "streamlit run dashboard/app.py"
    )


    subprocess.run(
        [
            "streamlit",
            "run",
            "dashboard/app.py"
        ]
    )

if __name__ == "__main__":

    run_dashboard()