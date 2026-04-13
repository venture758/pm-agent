## ADDED Requirements

### Requirement: Workbench MUST support manual maintenance of personnel profiles
系统必须允许用户在工作台中直接维护成员画像，并将该维护入口作为团队成员信息的唯一页面来源，不得再依赖 intake 阶段的临时成员录入。

#### Scenario: Open the personnel management view
- **WHEN** 用户进入人员管理页面
- **THEN** 系统展示当前工作区已维护的成员列表
- **THEN** 用户可以直接新增、编辑或删除成员画像

### Requirement: Personnel management MUST persist assignable member attributes
系统必须保存可用于分配和洞察的成员画像字段，至少包含姓名、角色、技能、经验、当前负载、容量和约束信息。

#### Scenario: Save a member profile from the maintenance page
- **WHEN** 用户在页面中编辑某成员画像并提交保存
- **THEN** 系统保存该成员的结构化画像字段
- **THEN** 后续推荐和洞察流程可以直接读取这些字段

### Requirement: Personnel management MUST validate invalid member profile input
系统必须在保存成员画像时校验空姓名、非法角色、负数负载或容量以及其他关键字段错误，不得将无效成员资料写入持久状态。

#### Scenario: Save a member profile with invalid capacity
- **WHEN** 用户保存某成员资料且容量字段为负数或明显无效
- **THEN** 系统拒绝保存该成员资料
- **THEN** 页面向用户展示对应字段的校验错误

### Requirement: Maintained personnel profiles MUST become the sole staffing source for recommendations
系统必须将已维护的成员画像作为推荐、监控和团队洞察的唯一人员来源，不得再接受 intake 阶段的临时成员覆盖输入。

#### Scenario: Generate recommendations from maintained personnel profiles
- **WHEN** 用户已经在人员管理页面维护过成员资料，随后在需求页面生成推荐
- **THEN** 系统仍能基于已维护的成员画像生成推荐结果
- **THEN** 用户不需要在需求处理页面重新填写临时成员表
