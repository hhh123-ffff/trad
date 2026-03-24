# 版本策略（Semantic Versioning）

本项目采用 [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html) 版本号规则：`MAJOR.MINOR.PATCH`。

## 1. 版本定义

- `MAJOR`：不兼容变更（例如 API 破坏性变更、核心数据模型不可兼容变更）。
- `MINOR`：向后兼容的新功能（新增模块、接口、页面、能力）。
- `PATCH`：向后兼容的问题修复（bugfix、稳定性修复、性能小优化）。

## 2. 当前版本

- 全局版本：`0.1.0`
- 后端版本来源：`backend/pyproject.toml` -> `[project].version`
- 前端版本来源：`frontend/package.json` -> `version`
- 根目录版本锚点：`VERSION`

## 3. 版本发布流程

1. 在 `CHANGELOG.md` 新增版本条目，记录 Added/Changed/Fixed。
2. 更新 `VERSION`。
3. 同步更新：
   - `backend/pyproject.toml` 的 `version`
   - `frontend/package.json` 的 `version`
4. 生成发布说明（`docs/releases/vX.Y.Z.md`）。
5. 执行验收：
   - `pytest -q`
   - `npm run build`
   - `docker compose ... config`
6. 打版本标签（可选）：`vX.Y.Z`。

## 4. 0.x 阶段约定

当前处于 `0.x` 快速迭代阶段：

- 允许在 `MINOR` 版本中进行中等规模重构。
- 若出现破坏性变更，仍建议提升 `MINOR` 并在发布说明中明确迁移步骤。
- 进入 `1.0.0` 前，应冻结核心 API 与数据库兼容策略。
