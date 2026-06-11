import os
import subprocess
import sys
from jinja2 import Environment, FileSystemLoader
from app.utils.resource_handler import get_resource_path

class PDFGenerator:
    def __init__(self, template_dir="assets/templates"):
        # Use the resource handler to find the templates folder
        # whether we are in VS Code or running as an .exe
        self.template_dir = get_resource_path(template_dir)
        
        # Configure Jinja2 to work with LaTeX syntax
        # We use raw strings (r'...') to prevent Python SyntaxWarnings
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            block_start_string=r'\BLOCK{',
            block_end_string='}',
            variable_start_string=r'\VAR{',
            variable_end_string='}',
            comment_start_string=r'\#{',
            comment_end_string='}',
            line_statement_prefix='%%',
            line_comment_prefix='%#',
            trim_blocks=True,
            autoescape=False,
        )

    def generate_tex(self, context, output_filename="output.tex"):
        """
        Renders the template with context data and saves a .tex file.
        """
        try:
            template = self.env.get_template("exam_template.tex")
            
            # Clean up image paths for LaTeX (Backslashes -> Forward slashes)
            if "questions" in context:
                for q in context["questions"]:
                    if hasattr(q, 'image_path') and q.image_path:
                        q.image_path = q.image_path.replace("\\", "/")

            tex_content = template.render(context)
            
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(tex_content)
                
            return True, output_filename
        except Exception as e:
            return False, f"{type(e).__name__}: {str(e)}"

    def compile_to_pdf(self, tex_file):
        """
        Tries to compile the .tex file to PDF using pdflatex.
        """
        try:
            # Added shell=False for security
            cmd = ['pdflatex', '-interaction=nonstopmode', tex_file]
            
            result = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            return True, tex_file.replace(".tex", ".pdf")
        except FileNotFoundError:
            return False, "pdflatex not found. Please install MiKTeX or TeX Live and ensure it's in your PATH."
        except subprocess.CalledProcessError as e:
            error_log = e.stdout[-500:] if e.stdout else "No output captured."
            return False, f"LaTeX Compilation Error:\n...{error_log}"