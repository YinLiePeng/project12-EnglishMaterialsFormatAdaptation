#!/usr/bin/env python3
"""
智能修正功能 - 端到端测试脚本
"""

import os
import sys
import time
import subprocess
import requests
import json
from pathlib import Path

# 配置
PROJECT_ROOT = Path("/mnt/e/Opencode/project12-EnglishMaterialsFormatAdaptation_2")
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
TEST_DOC = (
    PROJECT_ROOT
    / "测试用例/教师从网上下载的资料样例/M2U1 Food and drinks!（知识清单）英语牛津上海版试用本五年级下册[56534463].docx"
)
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

# 进程列表
processes = []


def print_section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_success(msg):
    print(f"✅ {msg}")


def print_error(msg):
    print(f"❌ {msg}")


def print_warning(msg):
    print(f"⚠️  {msg}")


def check_environment():
    """检查测试环境"""
    print_section("检查测试环境")

    # 检查Python
    print_success(f"Python版本: {sys.version.split()[0]}")

    # 检查测试文档
    if not TEST_DOC.exists():
        print_error(f"测试文档不存在: {TEST_DOC}")
        sys.exit(1)
    print_success(f"测试文档: {TEST_DOC.name}")

    # 检查后端虚拟环境
    if not (BACKEND_DIR / "venv").exists():
        print_error("后端虚拟环境不存在")
        sys.exit(1)
    print_success("后端虚拟环境存在")

    # 检查前端依赖
    if not (FRONTEND_DIR / "node_modules").exists():
        print_warning("前端依赖未安装，跳过前端测试")
    else:
        print_success("前端依赖已安装")

    print()


def start_backend():
    """启动后端服务"""
    print_section("启动后端服务")

    # 直接使用虚拟环境的Python来启动后端
    venv_python = BACKEND_DIR / "venv/bin/python"
    cmd = [
        str(venv_python),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]

    process = subprocess.Popen(
        cmd,
        cwd=str(BACKEND_DIR),
        stdout=open("/tmp/backend_stdout.log", "w"),
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid if os.name != "nt" else None,
    )
    processes.append(("backend", process))

    print(f"后端PID: {process.pid}")

    # 等待后端启动
    print("等待后端服务启动...", end="", flush=True)
    for i in range(30):
        try:
            response = requests.get(f"{BACKEND_URL}/api/v1/health", timeout=2)
            if response.status_code == 200:
                print_success("后端服务启动成功")
                print()
                return True
        except:
            pass
        time.sleep(1)
        print(".", end="", flush=True)

    print_error("后端服务启动失败")
    print("\n后端日志:")
    with open("/tmp/backend_stdout.log", "r") as f:
        print(f.read()[-500:])
    return False


def run_tests():
    """运行测试"""
    print_section("运行端到端测试")
    print()

    results = {}

    # 测试1: 健康检查
    print("测试1: 后端健康检查")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/health")
        if response.status_code == 200:
            # 只要返回200就认为是健康的
            print_success("健康检查通过")
            results["health_check"] = True
        else:
            print_error(f"健康检查失败，状态码: {response.status_code}")
            results["health_check"] = False
    except Exception as e:
        print_error(f"健康检查异常: {e}")
        results["health_check"] = False
    print()

    # 测试2: 上传文档
    print("测试2: 上传测试文档")
    try:
        with open(TEST_DOC, "rb") as f:
            files = {"file": f}
            data = {
                "layout_mode": "none",
                "preset_style": "universal",
                "enable_cleaning": "false",
                "enable_correction": "false",
                "enable_llm": "false",
            }
            response = requests.post(
                f"{BACKEND_URL}/api/v1/upload", files=files, data=data
            )

        if response.status_code == 200:
            result = response.json()
            task_id = result.get("data", {}).get("task_id")
            if task_id:
                print_success(f"文档上传成功，任务ID: {task_id}")
                results["upload_document"] = True
            else:
                print_error("上传响应中缺少task_id")
                results["upload_document"] = False
        else:
            print_error(f"上传失败，状态码: {response.status_code}")
            results["upload_document"] = False
    except Exception as e:
        print_error(f"上传异常: {e}")
        results["upload_document"] = False

    if not results.get("upload_document"):
        return results

    print()

    # 等待任务完成
    print("等待文档处理完成...", end="", flush=True)
    task_completed = False
    for i in range(60):
        try:
            response = requests.get(f"{BACKEND_URL}/api/v1/tasks/{task_id}")
            if response.status_code == 200:
                result = response.json()
                status = result.get("data", {}).get("status")
                if status == "completed":
                    print_success("文档处理完成")
                    task_completed = True
                    break
                elif status == "failed":
                    print_error("文档处理失败")
                    break
        except:
            pass
        time.sleep(1)
        print(".", end="", flush=True)

    if not task_completed:
        print_error("文档处理超时")
        return results

    print()

    # 测试3: 获取任务详情
    print("测试3: 获取任务详情和结构分析")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/tasks/{task_id}")
        if response.status_code == 200:
            result = response.json()
            structure = result.get("data", {}).get("structure_analysis")
            if structure:
                para_count = len(structure.get("paragraphs", []))
                print_success(f"获取到结构分析数据，共 {para_count} 个段落")
                results["get_task_details"] = True
            else:
                print_error("未获取到结构分析数据")
                results["get_task_details"] = False
        else:
            print_error(f"获取任务详情失败，状态码: {response.status_code}")
            results["get_task_details"] = False
    except Exception as e:
        print_error(f"获取任务详情异常: {e}")
        results["get_task_details"] = False

    print()

    # 测试4: 快速修正
    print("测试4: 快速修正功能")
    try:
        correction_data = {
            "paragraph_updates": [
                {"index": 0, "content_type": "title"},
                {"index": 1, "content_type": "heading"},
                {"index": 2, "content_type": "body"},
            ],
            "user_feedback": "端到端测试：修改前3个段落类型",
        }
        response = requests.post(
            f"{BACKEND_URL}/api/v1/tasks/{task_id}/quick-correction",
            json=correction_data,
        )

        if response.status_code == 200:
            result = response.json()
            updated_count = result.get("data", {}).get("updated_count")
            if updated_count == 3:
                print_success(f"快速修正成功，更新了 {updated_count} 个段落")
                results["quick_correction"] = True
            else:
                print_error(f"快速修正数量不对，期望3个，实际{updated_count}个")
                results["quick_correction"] = False
        else:
            print_error(f"快速修正失败，状态码: {response.status_code}")
            results["quick_correction"] = False
    except Exception as e:
        print_error(f"快速修正异常: {e}")
        results["quick_correction"] = False

    print()

    # 测试5: 重新生成文档
    print("测试5: 重新生成文档")
    try:
        response = requests.post(f"{BACKEND_URL}/api/v1/tasks/{task_id}/regenerate")

        if response.status_code == 200:
            result = response.json()
            output_file = result.get("data", {}).get("output_filename")
            if output_file:
                print_success(f"文档重新生成成功")
                print(f"   输出文件: {output_file}")
                results["regenerate_document"] = True
            else:
                print_error("重新生成响应中缺少output_filename")
                results["regenerate_document"] = False
        else:
            print_error(f"重新生成失败，状态码: {response.status_code}")
            results["regenerate_document"] = False
    except Exception as e:
        print_error(f"重新生成异常: {e}")
        results["regenerate_document"] = False

    print()

    # 测试6: 下载文档
    print("测试6: 下载生成的文档")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/tasks/{task_id}/download")

        if response.status_code == 200:
            file_size = len(response.content)
            print_success(f"文档下载成功，大小: {file_size} 字节")

            # 保存下载的文件
            with open("/tmp/e2e_test_download.docx", "wb") as f:
                f.write(response.content)

            results["download_document"] = True
        else:
            print_error(f"文档下载失败，状态码: {response.status_code}")
            results["download_document"] = False
    except Exception as e:
        print_error(f"文档下载异常: {e}")
        results["download_document"] = False

    print()

    return results, task_id


def cleanup():
    """清理进程"""
    print_section("清理测试环境")

    for name, process in processes:
        try:
            print(f"停止{name}服务 (PID: {process.pid})...")
            if os.name != "nt":
                os.killpg(os.getpgid(process.pid), 15)  # SIGTERM
            else:
                process.terminate()
            process.wait(timeout=5)
        except:
            try:
                process.kill()
            except:
                pass

    print_success("清理完成")


def main():
    """主函数"""
    print_section("智能修正功能 - 端到端测试")
    print()

    try:
        # 检查环境
        check_environment()

        # 启动后端
        if not start_backend():
            cleanup()
            sys.exit(1)

        # 运行测试
        try:
            results, task_id = run_tests()
        except Exception as e:
            print(f"测试运行异常: {e}")
            results = {}
            task_id = None

        # 统计结果
        passed = sum(1 for v in results.values() if v)
        total = len(results)

        print_section("测试结果")
        print()
        for test_name, passed_flag in results.items():
            status = "✅ 通过" if passed_flag else "❌ 失败"
            print(f"  {test_name.replace('_', ' ').title()}: {status}")

        print()
        print(f"总计: {passed}/{total} 测试通过")

        if task_id:
            print(f"任务ID: {task_id}")

        # 保存测试结果
        test_output = {
            "test_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "task_id": task_id,
            "tests": results,
            "summary": {"total": total, "passed": passed, "failed": total - passed},
        }

        with open("/tmp/e2e_test_results.json", "w") as f:
            json.dump(test_output, f, indent=2)

        print(f"\n测试结果已保存到: /tmp/e2e_test_results.json")

        if passed == total:
            print()
            print_section("🎉 所有测试通过！")
            sys.exit(0)
        else:
            print()
            print_error("部分测试失败")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
