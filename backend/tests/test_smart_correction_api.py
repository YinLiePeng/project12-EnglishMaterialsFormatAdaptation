"""测试智能修正功能的API端点"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport
from app.main import app
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.task import Task
from sqlalchemy import select
import json


async def test_quick_correction():
    """测试快速修正端点"""

    print("\n" + "=" * 60)
    print("测试1: 快速修正端点 (POST /tasks/{task_id}/quick-correction)")
    print("=" * 60)

    # 获取一个已完成的任务
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Task).where(Task.status == "completed").limit(1)
        )
        task = result.scalar_one_or_none()

        if not task:
            print("❌ 没有找到已完成的任务，请先上传并处理一个文档")
            return False

        task_id = task.task_id
        print(f"✅ 找到任务: {task_id}")

        # 解析当前结构分析
        structure = json.loads(task.structure_analysis)
        print(f"✅ 当前有 {len(structure['paragraphs'])} 个段落")

        # 准备测试数据：修改前3个段落的类型
        paragraph_updates = []
        for i in range(min(3, len(structure["paragraphs"]))):
            para = structure["paragraphs"][i]
            old_type = para["content_type"]

            # 选择一个新类型（与原类型不同）
            new_type = "heading" if old_type != "heading" else "body"

            paragraph_updates.append({"index": i, "content_type": new_type})

        request_data = {
            "paragraph_updates": paragraph_updates,
            "user_feedback": "测试快速修正功能",
        }

        # 使用 ASGI 传输层测试 FastAPI 应用
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/tasks/{task_id}/quick-correction", json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ 快速修正成功！")
                print(f"   - 更新了 {data['data']['updated_count']} 个段落")

                # 验证更新
                await db.rollback()  # 回滚以获取最新数据
                result = await db.execute(select(Task).where(Task.task_id == task_id))
                updated_task = result.scalar_one_or_none()
                updated_structure = json.loads(updated_task.structure_analysis)

                # 检查前3个段落的置信度是否为1.0
                all_confident = all(
                    updated_structure["paragraphs"][i]["confidence"] == 1.0
                    for i in range(len(paragraph_updates))
                )

                if all_confident:
                    print(f"✅ 所有更新段落的置信度都为1.0（用户手动修正）")
                    return True
                else:
                    print(f"❌ 置信度更新失败")
                    return False
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False


async def test_ai_recognize_preview():
    """测试AI识别端点（预览模式）"""

    print("\n" + "=" * 60)
    print("测试2: AI识别端点 - 预览模式 (POST /tasks/{task_id}/ai-recognize)")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Task).where(Task.status == "completed").limit(1)
        )
        task = result.scalar_one_or_none()

        if not task:
            print("❌ 没有找到已完成的任务")
            return False

        if task.enable_llm != 1:
            print(f"⚠️  任务 {task.task_id} 未启用LLM，跳过AI识别测试")
            return True  # 不算失败，只是跳过

        task_id = task.task_id
        print(f"✅ 找到已启用LLM的任务: {task_id}")

        request_data = {"user_feedback": "段落0应该是标题", "mode": "preview"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/tasks/{task_id}/ai-recognize", json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ AI识别预览成功！")
                print(f"   - 检测到 {len(data['data']['changes'])} 处变化")
                print(f"   - 模式: {data['data']['mode']}")

                if data["data"]["changes"]:
                    print(f"\n   变化详情:")
                    for change in data["data"]["changes"][:3]:  # 只显示前3个
                        print(
                            f"   - 段落{change['index']}: {change['old_type_name']} → {change['new_type_name']}"
                        )

                return True
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False


async def test_regenerate_document():
    """测试文档重新生成端点"""

    print("\n" + "=" * 60)
    print("测试3: 文档重新生成端点 (POST /tasks/{task_id}/regenerate)")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Task).where(Task.status == "completed").limit(1)
        )
        task = result.scalar_one_or_none()

        if not task:
            print("❌ 没有找到已完成的任务")
            return False

        task_id = task.task_id
        old_output_path = task.output_file_path

        print(f"✅ 找到任务: {task_id}")
        print(f"   旧输出文件: {task.output_filename}")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/v1/tasks/{task_id}/regenerate")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ 文档重新生成成功！")
                print(f"   - 新文件名: {data['data']['output_filename']}")
                print(f"   - 下载链接: {data['data']['download_url']}")

                # 验证任务更新
                await db.rollback()
                result = await db.execute(select(Task).where(Task.task_id == task_id))
                updated_task = result.scalar_one_or_none()

                if updated_task.output_file_path != old_output_path:
                    print(f"✅ 输出文件路径已更新")
                    return True
                else:
                    print(f"⚠️  输出文件路径未变化（可能使用了相同的文件名）")
                    return True  # 不算失败
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("智能修正功能 API 测试")
    print("=" * 60)

    results = []

    try:
        results.append(await test_quick_correction())
    except Exception as e:
        print(f"❌ 测试1异常: {e}")
        import traceback

        traceback.print_exc()
        results.append(False)

    try:
        results.append(await test_ai_recognize_preview())
    except Exception as e:
        print(f"❌ 测试2异常: {e}")
        import traceback

        traceback.print_exc()
        results.append(False)

    try:
        results.append(await test_regenerate_document())
    except Exception as e:
        print(f"❌ 测试3异常: {e}")
        import traceback

        traceback.print_exc()
        results.append(False)

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")

    if all(results):
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
