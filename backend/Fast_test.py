import opendataloader_pdf

# Batch all files in one call — each convert() spawns a JVM process, so repeated calls are slow
opendataloader_pdf.convert(
    input_path=["./测试用例/M2U1 Food and drinks!（知识清单）英语牛津上海版试用本五年级下册[56534463].pdf"],
    output_dir="./测试用例",
    format="markdown,json"
)