import opendataloader_pdf

# Batch all files in one call — each convert() spawns a JVM process, so repeated calls are slow
opendataloader_pdf.convert(
    input_path=["测试用例/原生PDF/"],
    output_dir="output_fast_outputPDF/",
    format="json,markdown,pdf",
    image_output="embedded",        # "off", "embedded" (Base64), or "external" (default)
    image_format="jpeg",            # "png" or "jpeg"
    use_struct_tree=True,           # Use native PDF structure
)