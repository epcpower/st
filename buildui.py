import alqtendpy.compileui
import pathlib

def compile_ui():
    alqtendpy.compileui.compile_ui(
       directory_paths=[pathlib.Path(__file__).parent / "src" / "epyq"],
    )
    alqtendpy.compileui.compile_ui(
       directory_paths=[pathlib.Path(__file__).parent / "sub" / "epyqlib" / "epyqlib"],
    )
