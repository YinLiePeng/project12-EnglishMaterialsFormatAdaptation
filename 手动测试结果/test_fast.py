import opendataloader_pdf

# Batch all files in one call — each convert() spawns a JVM process, so repeated calls are slow
opendataloader_pdf.convert(
    input_path=["测试用例/原生PDF/"],
    output_dir="output_fast/",
    format="markdown,json"
)