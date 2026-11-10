# 网申与求职申请 Skills

根据用户自己的履历，在已登录的招聘网站中批量填写申请表，按真实保存范围核验并保留恢复记录。包含完整 Python/Node 执行源码和独立的招聘批次筛选 skill。表单控件、模型和网站限制可能阻塞流程，不保证兼容所有招聘网站。

本仓库由现有 [job-application-autofill](https://github.com/cyyecao-lappland/job-application-autofill) 安装包整理，保留原 MIT 许可证。移除了本机配置、私有映射、个人材料、历史运行数据和历史申请专用脚本。此仓库公开，任何人均可克隆源码。

## 安装主 skill

需要 Git、Python 3.11+、Node.js（原项目在 Node.js 24 验证）、Microsoft Edge，以及可用且已登录的 Codex CLI。陌生字段及独立模型核验默认使用 `gpt-6-luna`；用户可在本机配置中明确选择自己账号可用的模型，目标宿主必须提供实际模型/子代理能力。能力不可用时应报告阻塞，不能声称核验已完成。依赖安装可能联网，模型调用可能产生费用。

macOS/Linux：

```sh
mkdir -p "$HOME/.agents/skills"
git clone https://github.com/iriszzz-lab/job-application-autofill.git "$HOME/.agents/skills/job-application-autofill"
cd "$HOME/.agents/skills/job-application-autofill"
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[resume]"
npm ci
```

Windows PowerShell：

```powershell
$skillDir = Join-Path $env:USERPROFILE '.agents/skills/job-application-autofill'
git clone https://github.com/iriszzz-lab/job-application-autofill.git $skillDir
Set-Location $skillDir
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[resume]"
npm ci
```

已有同名目录时不要覆盖或重跑克隆。先确认 `python3.12 --version`（Windows 用 `python --version`）为 3.11 或以上；如使用其他符合要求的 Python，请替换命令中的可执行文件名。

安装后调用 `$job-application-autofill`；如未发现，重启宿主。源目录就是 skill 和执行项目，无需另找外部程序。更新时在此目录运行 `git pull --ff-only`，不要用模板覆盖已有私有状态。

## 第一次使用：上传自己的简历

新用户直接在聊天中上传自己的 PDF、DOCX、TXT/Markdown 或图片简历，也可以指定本地路径，例如：

> 使用 $job-application-autofill。我已上传自己的简历，请先识别全部内容，按客观事实建立我的私有资料，列出无法辨认、冲突和缺失信息。暂不操作招聘网站。

AI 按 [简历导入流程](references/resume-onboarding.md) 识别不同版式、中英文标题和多页经历，并生成规范 JSON。PDF 与 DOCX 辅助提取命令为：

```sh
.venv/bin/python scripts/prepare_resume.py --input /absolute/private/resume.pdf --output /absolute/private/resume-source.json
```

Windows 将 Python 路径替换为 `.venv\Scripts\python.exe`。提取结果只保留源文和位置，不直接宣布事实已核验。扫描 PDF、图片或复杂双栏由宿主视觉读取或可用 OCR 辅助，逐页核对；没有这些能力时明确交接，不能假装已读。旧 DOC 请使用可用转换工具，或另存 PDF/DOCX。

事实保留文件、页码/段落和原文引文；缺失用 null，不编造日期、成果、奖项或资格。用户只需核对摘要并补充真正缺失的信息，不必手工填写整份 JSON。上传简历只用于整理资料，网站填写、暂存和提交仍按你的当前授权进行。个人资料及原简历保存在仓库之外。

也支持复用已有 JSON，或使用 [空白模板](templates/autofill-profile.template.json)。规范字段为 `education[].school_name`、`employment[]`；旧资料的 `school` 与 `internships` 保持兼容。删除不用的占位记录，核对来源后设置 `example_only: false`。细节见 [资料格式](references/profile-format.md)。

资料准备好后，在仓库根目录执行（替换为自己的绝对路径）：

```sh
# macOS/Linux
.venv/bin/python scripts/init_local_config.py --profile /absolute/private/autofill-profile.json
.venv/bin/python scripts/resolve_config.py
```

```powershell
# Windows
.\.venv\Scripts\python.exe scripts/init_local_config.py --profile 'C:\your-private-folder\autofill-profile.json'
.\.venv\Scripts\python.exe scripts/resolve_config.py
```

需要其他模型时，初始化命令可增加 `--semantic-model <实际模型名> --review-model <实际模型名>`，或修改已有 `private/local-config.json` 的对应键；不会自动回退到另一模型。

初始化仅创建忽略提交的 `config.local.json`、`private/local-config.json` 和空白 `private/form-knowledge.json`，拒绝覆盖已有配置或映射，也不连接浏览器。已有用户直接修改自己的配置，按 [本机配置与迁移](references/installation-config.md) 核对。运行记录使用配置解析的 `prior_root`（默认 `private/`），个人简历附件和资料留在仓库外。

`ready` 只表示必要路径存在。它不证明模型、浏览器、网页填写或保存可用。

## 浏览器与第一次使用

Windows 用户可运行根目录 `install-edge.cmd` 创建独立 Edge 配置和本机 CDP 端口，细节见 [Windows Edge 部署](docs/windows-edge-setup.md)。脚本可能安装 Edge 并启动浏览器，按需自行运行。

macOS 在自己确认的新专用用户目录上启动 Edge，例如：

```sh
"/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9333 --user-data-dir="$HOME/.job-application-edge"
```

Linux 使用系统实际 Edge 可执行文件，传入相同参数。CDP 只绑定本机；使用自己的专用浏览器资料目录，首次手动登录招聘网站，不复制他人 Cookie 或会话。已经有 CDP 浏览器时复用它，将真实端口写入 `config.local.json`。普通浏览器标签页不会因安装 skill 自动变成可控页面。

先自行打开申请表，再向助手明确指定页面和权限，例如：

> 使用 $job-application-autofill。先读取我的本机配置，只读勘察指定的申请页并报告缺项，暂不填写或提交。

> 使用我的资料填写并暂存这个指定岗位，不正式提交。缺失信息集中交接。

正式提交需要当前用户明确授权。克隆或安装不代表填写、保存、提交或自动寻岗授权；他人的授权、城市偏好和毕业年份不会继承。提交结果未知时先核对当前账号记录，不能盲目重投。中断后沿用原运行目录与 journal，保留手动修改。执行参数见 [执行程序说明](docs/executor-guide.md)。

## 可选：招聘批次筛选

[recruitment-batch-screening](skills/recruitment-batch-screening/SKILL.md) 是独立 skill。从本仓库复制该目录到自己的 `~/.agents/skills/recruitment-batch-screening`（已有目录时先检查，避免覆盖），或用宿主的 skill 安装器选择此子目录。更新主仓库后需单独更新副本。

筛选脚本只依赖 Python 标准库。必须配置自己的履历、筛选偏好、候选来源和经确认的真实去重台账；公开配置不绑定任何人的历史。没有历史的新用户也应显式创建并确认自己的空台账，不能把缺失文件当空名单。实时官网核验需要宿主可用的浏览器与独立子代理；该 skill 不提交申请。

## 离线检查

以下命令不操作招聘网站，也不进行真实模型调用：

```sh
.venv/bin/python -m edge_form_graph.application_cli --help
node scripts/build_control_registry.mjs --check
.venv/bin/python -B -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python -B -m unittest discover -s scripts -p 'test_*.py'
.venv/bin/python -B -m unittest discover -s skills/recruitment-batch-screening/scripts -p 'test_*.py'
node --test tests/test_*.mjs
```

Windows 将 Python 路径替换为 `.venv\Scripts\python.exe`。Node 集成测试需 `python` 在 PATH 中可用，可先激活虚拟环境。需真实 Chromium 的测试由安装者按测试说明准备本机环境；离线测试通过不证明现场申请成功。

本次打包的验证结果见 [安装验证记录](docs/installation-validation.md)。

## 隐私与发布

只提交通用代码、空模板和合成测试。`.gitignore` 排除个人配置、`private/`、运行记录、截图、简历附件、浏览器目录和依赖环境，但它不能阻止强制添加或任意命名的个人文件。提交前检查 `git diff --cached`，不要上传简历、证件、邮箱/手机号、Cookie、令牌、截图、真实申请结果或本机路径。模型运行会接收任务所需的个人资料，应由资料所有者自行决定是否使用。

[MIT License](LICENSE)
