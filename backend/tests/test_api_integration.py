"""API集成测试 - 测试PDF上传和处理的完整流程"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
import asyncio

BASE_URL = "http://localhost:8000/api/v1"

TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "测试用例")
NATIVE_DIR = os.path.join(TEST_DIR, "原生PDF")
IMAGE_DIR = os.path.join(TEST_DIR, "图片型PDF")


async def test_upload_native_pdf():
    """测试上传原生PDF文件"""
    print("\n=== 测试1: 上传原生PDF (不使用LLM) ===")

    files = os.listdir(NATIVE_DIR)
    pdf_files = [f for f in files if f.endswith(".pdf")]
    test_file = os.path.join(NATIVE_DIR, pdf_files[0])

    print(f"  文件: {pdf_files[0][:50]}...")

    async with httpx.AsyncClient(timeout=60) as client:
        with open(test_file, "rb") as f:
            response = await client.post(
                f"{BASE_URL}/upload",
                files={"file": (pdf_files[0], f, "application/pdf")},
                data={
                    "layout_mode": "none",
                    "preset_style": "universal",
                    "use_llm": "false",
                },
            )

        print(f"  状态码: {response.status_code}")
        data = response.json()
        print(f"  返回code: {data.get('code')}")

        if data.get("code") != 0:
            print(f"  错误: {data}")
            return False

        result = data.get("data", {})
        task_id = result.get("task_id")
        is_pdf = result.get("is_pdf")
        pdf_detection = result.get("pdf_detection")

        print(f"  task_id: {task_id}")
        print(f"  is_pdf: {is_pdf}")

        if pdf_detection:
            print(f"  PDF类型检测: {pdf_detection.get('type')} ({pdf_detection.get('type_name')})")
            print(f"  置信度: {pdf_detection.get('confidence')}")
            print(f"  总页数: {pdf_detection.get('total_pages')}")
            print(f"  处理提示: {pdf_detection.get('processing_hint')}")

        assert is_pdf == True, "应标记为PDF文件"
        assert pdf_detection is not None, "应有PDF类型检测结果"
        assert pdf_detection.get("type") == "native", f"应为native类型, 实际={pdf_detection.get('type')}"

        print("  等待后台处理...")
        for i in range(30):
            await asyncio.sleep(2)
            status_resp = await client.get(f"{BASE_URL}/tasks/{task_id}")
            status_data = status_resp.json().get("data", {})
            status = status_data.get("status")
            print(f"  [{i*2}s] 状态: {status}")

            if status == "completed":
                print(f"  处理完成! 耗时: {status_data.get('processing_time')}s")
                print(f"  输出文件: {status_data.get('output_filename')}")

                dl_resp = await client.get(f"{BASE_URL}/tasks/{task_id}/download")
                print(f"  下载状态码: {dl_resp.status_code}")
                assert dl_resp.status_code == 200, "应能下载结果文件"
                assert len(dl_resp.content) > 0, "文件内容不应为空"
                print(f"  文件大小: {len(dl_resp.content)} bytes")
                return True

            if status == "failed":
                print(f"  处理失败: {status_data.get('error_message')}")
                return False

        print("  超时!")
        return False


async def test_upload_image_pdf():
    """测试上传图片型PDF - 验证类型检测正确 + OCR降级提示"""
    print("\n=== 测试2: 上传图片型PDF (验证类型检测和OCR降级) ===")

    files = os.listdir(IMAGE_DIR)
    pdf_files = [f for f in files if f.endswith(".pdf")]
    test_file = os.path.join(IMAGE_DIR, pdf_files[0])

    print(f"  文件: {pdf_files[0][:50]}...")

    async with httpx.AsyncClient(timeout=60) as client:
        with open(test_file, "rb") as f:
            response = await client.post(
                f"{BASE_URL}/upload",
                files={"file": (pdf_files[0], f, "application/pdf")},
                data={
                    "layout_mode": "none",
                    "preset_style": "universal",
                    "use_llm": "false",
                },
            )

        print(f"  状态码: {response.status_code}")
        data = response.json()
        print(f"  返回code: {data.get('code')}")

        if data.get("code") != 0:
            print(f"  错误: {data}")
            return False

        result = data.get("data", {})
        pdf_detection = result.get("pdf_detection")

        if pdf_detection:
            print(f"  PDF类型检测: {pdf_detection.get('type')} ({pdf_detection.get('type_name')})")
            assert pdf_detection.get("type") == "scanned", f"应为scanned, 实际={pdf_detection.get('type')}"
            print(f"  [PASS] 类型检测正确: scanned")

        task_id = result.get("task_id")
        print("  等待后台处理...")
        for i in range(30):
            await asyncio.sleep(2)
            status_resp = await client.get(f"{BASE_URL}/tasks/{task_id}")
            status_data = status_resp.json().get("data", {})
            status = status_data.get("status")
            print(f"  [{i*2}s] 状态: {status}")

            if status in ("completed", "failed"):
                if status == "completed":
                    print(f"  [PASS] OCR处理成功")
                    return True
                else:
                    err = status_data.get("error_message", "")
                    if "OCR" in err or "API密钥" in err:
                        print(f"  [PASS] OCR降级提示正确: {err[:60]}")
                        return True
                    else:
                        print(f"  [FAIL] 错误信息不友好: {err}")
                        return False

        return False


async def test_multiple_native_pdfs():
    """测试多个原生PDF文件"""
    print("\n=== 测试3: 批量测试原生PDF ===")

    files = sorted(os.listdir(NATIVE_DIR))
    pdf_files = [f for f in files if f.endswith(".pdf")][:5]

    async with httpx.AsyncClient(timeout=60) as client:
        results = []
        for fname in pdf_files:
            test_file = os.path.join(NATIVE_DIR, fname)
            with open(test_file, "rb") as f:
                response = await client.post(
                    f"{BASE_URL}/upload",
                    files={"file": (fname, f, "application/pdf")},
                    data={
                        "layout_mode": "none",
                        "preset_style": "universal",
                        "use_llm": "false",
                    },
                )

            data = response.json()
            detection = data.get("data", {}).get("pdf_detection", {})
            det_type = detection.get("type", "?") if detection else "?"
            pages = detection.get("total_pages", "?") if detection else "?"

            results.append((fname[:40], det_type, pages, data.get("code")))
            print(f"  {fname[:40]:<40} type={det_type:<8} pages={pages} code={data.get('code')}")

        all_ok = all(r[3] == 0 for r in results)
        print(f"  结果: {'全部成功' if all_ok else '有失败'}")
        return all_ok


async def main():
    print("=" * 60)
    print("PDF处理 API 集成测试")
    print("=" * 60)

    try:
        r1 = await test_upload_native_pdf()
    except Exception as e:
        print(f"  测试1异常: {e}")
        r1 = False

    try:
        r2 = await test_upload_image_pdf()
    except Exception as e:
        print(f"  测试2异常: {e}")
        r2 = False

    try:
        r3 = await test_multiple_native_pdfs()
    except Exception as e:
        print(f"  测试3异常: {e}")
        r3 = False

    print("\n" + "=" * 60)
    print(f"测试1 (原生PDF上传+处理+下载): {'PASS' if r1 else 'FAIL'}")
    print(f"测试2 (图片型PDF上传+类型检测): {'PASS' if r2 else 'FAIL'}")
    print(f"测试3 (批量原生PDF上传):        {'PASS' if r3 else 'FAIL'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
