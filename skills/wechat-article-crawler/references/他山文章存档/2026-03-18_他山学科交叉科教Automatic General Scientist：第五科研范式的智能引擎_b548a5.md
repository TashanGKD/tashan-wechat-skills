---
title: "他山学科交叉科教|Automatic General Scientist：第五科研范式的智能引擎"
source: 他山学科交叉
source_type: wechat
url: "https://mp.weixin.qq.com/s/IdpNIBOBJlNN6Ys42LvdTw"
author: 他山学科交叉
scraped_at: 2026-03-18T22:15:14.954913+00:00
content_type: full
---

# 他山学科交叉科教|Automatic General Scientist：第五科研范式的智能引擎

内容摘要

1、AI**发展新趋势：大模型正朝向私有域数据挖掘及物理世界交互并行演进。**

**2、AGS****实现框架：以"假设生成→实验验证→反思迭代"为核心，通过内循环（规划反思）与外循环（行动感知）提升科研自动化流程的稳定性、可迭代性。**

**3、AGS****现状与未来：由Level 0（纯人工）至Level 5（全自主）的演化路径，明确各阶段人机协作模式、知识积累效率阈值及应用场景特征。**

**4、****学科渗透差异：虚拟环境实验主导（比如数学/生信）已形成初步闭环，物理环境实验依赖（如医学/纳米材料）实现全流程智能化具备挑战。**

**（全文约2800字，阅读时间约7分钟）**

**以下内容整理自2025年5月5日他山跨学科交流计划·硬科普报告：“Automatic General Scientist：第五科研范式的智能引擎”，报告人为中国科学院大学天文学院博士生、他山学科交叉创新协会联合创始人李瑀旸。**

**01**

**AI****新趋势：从通用走向纵深，从虚拟迈向现实**

在年初DeepSeek R1发布后的小组讨论中，我们推测大模型发展将会顺应两个趋势：

![](https://mmbiz.qpic.cn/mmbiz_png/YfcILJIWTS8GaJ1xlAzfib02GoeuNQd3RgpL8Iqo6ItwvKmKqBNU8wfoeovNcLAIXjA5qSia0gfBUN10kLK0FEqQ/640?wx_fmt=png&from=appmsg)

一、私有域知识深度挖掘：“搜索”到“研究”

从Anthropic在5月2号发布的「Integrations」集成功能和「Advanced Research」高级研究能力中，我们可以看到模型将不再仅仅是通用信息的处理器，而是开始向个人环境的“知识专家”转变。这个过程除了链接已有私有数据，“人在回路”（human-in-the-loop）的反馈数据在此过程中也将扮演至关重要的角色：以Qwen3发布后对通义团队负责人的采访可以看出，他们下一目标是推动模型从当前的“被动式学习”向更主动的学习模式演进，其中包括了实现自我反思及人机协同中的在线学习（OnlineLearning）、支持持续学习（ContinualLearning）并最终迈向真正的自学习（Self-Learning）能力。

二、与物理世界交互的边界扩展

从商业化的Claude Computer Use -> Manus-> AutoGLM，开源的ShowUI -> OminiParse2 -> UI-TARS-1.5，大模型在通用任务上逐步探索基于Computer Use探索拓展能力边界。而对于AI4S，更广义的仪器使用（Instrument Use）及物理世界交互，是科学任务中AI Assistant向AI Partner转变的关键。

**02**

**什么是AGS：AI能否自主完成科学发现？**

人工智能正在重塑科研的底层逻辑和工作方式，推动科研决策从经验驱动转向模型分析、工具使用从人工操作转向智能协同、科研组织从封闭独立转向跨学科共享，这个新阶段被称为第五科研范式。近日，由《Scaling Laws in Scientific Discovery with AI and Robot Scientists》所提出的“自动通用科学家”（AGS, Automatic General Scientist）的概念引起了广泛关注，我们也根据这篇文章来梳理当前AI4S的进展并推测未来科研模式可能的发展方向。

![](https://mmbiz.qpic.cn/mmbiz_png/YfcILJIWTS8GaJ1xlAzfib02GoeuNQd3RcEQVlhgcSYALF3IvGAqvGBDIY39kgqickmRbDLicWzuibhs2q9QWTfLNQ/640?wx_fmt=png&from=appmsg)

![](https://mmbiz.qpic.cn/mmbiz_png/YfcILJIWTS8GaJ1xlAzfib02GoeuNQd3RwNZhib4aibz6En55C0AuopwGbj2HqkEmiaibFw7iaTibnEmapg5nTUibv60Sg/640?wx_fmt=png&from=appmsg)

对于当前科学发展，人机协同有效地加快了知识积累进程，但整体仍然受到知识边界与物理边界的限制。而AGS有望打破这个边界，通过两个飞轮相互关联，共同提升认知激发需求：

![](https://mmbiz.qpic.cn/mmbiz_png/YfcILJIWTS8GaJ1xlAzfib02GoeuNQd3RvibsPSPwjhzVia1sYFsgWESmFmzSB0OLYBTz3vsoZ0a3PhzM6cibqJEeA/640?wx_fmt=png&from=appmsg)

知识飞轮：从人类需求（Needs）出发，AI 科学家（AI Scientists）和机器人科学家（Robot Scientists）开展研究（Research），产生科学（Science）知识，进而积累知识（Knowledge），完成一个循环。

物理飞轮：人类需求（Needs）催生技术（Technology），技术推动工程（Engineering）发展，工程促进社会（Society）进步，社会发展依托自然（Nature），最终与宇宙（Universe）关联，整体影响文明（Civilization）进程，完成另一个循环。

![](https://mmbiz.qpic.cn/mmbiz_png/YfcILJIWTS8GaJ1xlAzfib02GoeuNQd3RdQaAb6FIZBFG1eIXxkhyxicdy9tzsWcoGaOxbbxeFoB4mFL0QQ90Mhw/640?wx_fmt=png&from=appmsg)\

如何实现AGS？我们去年的研究《StarWhisper Telescope: Agent-Based Observation Assistant System to Approach AI Astrophysicist》提出了一个AGS  实现框架（如上图）。该框架的核心是：首先，基于现有图文知识库、领域数据库进行假设生成（Idea Generation），随后通过物理环境实验（Physical Experiment）与虚拟实验（Virtual Experiment）进行验证，最后是基于数据分析和报告撰写进行反思（Reflection）对下一轮假设进行修正等步骤。\

![](https://mmbiz.qpic.cn/mmbiz_png/YfcILJIWTS8GaJ1xlAzfib02GoeuNQd3RDqLQ9bHH6yAdpYiatwjQSl0JibVY8sSV35ue7f1ZLkOjftUKFDRVja3Q/640?wx_fmt=png&from=appmsg)

与之类似，原文中提出的AGS框架如上图所示，进一步印证了这类基于科学哲学与经验闭环流程的通用性。即数据查询分析（Literature review）-> 给出研究提案（Proposal）-> 虚拟/物理环境实验（Experiment）验证 -> 分析整理并撰写研究手稿（Manuscript）。在撰写和总结过程中，通过反思（Reflection）得到的内容将被储存到记忆库中，从而影响模型在下一轮决策和交互中的表现。同时该框架同样强调了“人在回路”的重要性，在科研各个主要环节中都加入了多轮人机交互。

![](https://mmbiz.qpic.cn/mmbiz_png/YfcILJIWTS8GaJ1xlAzfib02GoeuNQd3RkHPKU6SCq6S5gA2jL6yl52Yiaia5vMEbia2qWiajVIehqPmcruKMC3XgGA/640?wx_fmt=png&from=appmsg)

上图详细的介绍了框架的核心运作机制：

内循环（Inner Loop）——“规划与反思”：基于预设知识与自我反思产生的记忆（Memory），结合当前从外部接收到的信息（无论是人类指令还是传感器反馈数据）进行推理规划与决策。

外循环（Outer Loop）——“行动与感知”：决策执行具体动作时，利用各种工具（Tools），包括在虚拟环境中运行的软件工具（Virtual Tools），也可以是具身智能（EmbodiedRobot）在物理环境中的具体操作，在与外界环境交互后收集反馈。

03

AI科学家的“进化之路”：从助手到探索者分几步？

![](https://mmbiz.qpic.cn/mmbiz_png/YfcILJIWTS8GaJ1xlAzfib02GoeuNQd3RbzkianZUkva0gD58sfHNuLMGCibjPHsWqArWXibBVYA5KyIgJibsZOk2Ww/640?wx_fmt=png&from=appmsg)

按照AGS的定义，各等级如下：

- Level 0——完全由人进行：这是科研的起点，没有任何AI的介入，所有的工作，从实验设计到数据分析，均由人类科学家独立完成。

- Level1——工具辅助：AI开始作为辅助工具出现，不论是统计与机器学习、深度学习算法，还是例如使用ChatGPT进行文献初步检索或代码编写。整个研究过程仍由人类主导，AI提供简单任务协助。目前大多数科研使用场景。

- Level 2——智能助手：随着AI能力增强，能够整合更广泛的图文数据，并执行一些复杂的虚拟任务，例如OpenDev、DeepResearch等工具所展现的能力。但此阶段AI的工作仍需人类的密切监督，且主要集中在虚拟任务，尚未深度介入实验数据获取与处理分析。

- Level 3——合作伙伴：这是一个重要的转折点。AI与人类科学家逐渐成为协作关系，能够同时处理虚拟和物理环境中的任务。国内已有的相关探索案例，如中科大的机器化学家、松山湖材料实验室的机器人材料科学家以及国家天文台研发的星语系统等。在此阶段，AI可能负责实验的具体操作，而人类科学家则提供更高层面的指导和策略。

- Level 4——研究员：AI开始主导研究的全流程，从提出假设、设计实验到分析结果、撰写论文，人类科学家的角色转变为关键节点决策者和最终审核者。例如设想中的AGIRobot (AGIR)，以及目前处于Level 4的几个团队都在整合数据、管道、仪器向这个方向发展。近期MCP（模型调用协议）的不断发展，以及像DeepSeek R1、Qwen3这类具备“慢思考”的模型能力进步，为实现这一阶段提供了技术基础。

- Level 5——探索者：能够独立进行科学创新，但尚属于对未来的展望，缺乏明确的定量衡量标准。

**![](https://mmbiz.qpic.cn/mmbiz_png/YfcILJIWTS8GaJ1xlAzfib02GoeuNQd3R23HxPueh2M5fnAsG5iboTtlyxOtVda9S4bUqJEg8wVGFOFjHqicqLtGA/640?wx_fmt=png&from=appmsg)![]()![]()![]()![]()![]()![]()![]()**

目前前沿研究主要集中在实验环境交互（Robot）的完善阶段。而这里所标准的203x时间节点，不仅是AI科学家发展的边界，也是当前广义数字员工突破的一个瓶颈。即不再依赖预设业务背景的固定工作流，是【模型能力】能够自主规划完成复杂任务，且【工具生态】足够囊括大部分场景的自动化工作流。

文中详细梳理了众多学科及其子领域，对虚拟（Virtual）操作 （如模拟、计算、数据分析）和物理（Physical）操作（如实验操作、样品制备、实地观测）所占流程比重统计结果也与我们之前AI4S实践经验一致：

- 在虚拟操作占比较高的学科，AGS模式初具雏形：

- 数学：在纯粹的逻辑推理与符号运算领域，从最早期支持 Lean3的InternLMMath到近期支持Lean4的DeepSeekProve 2，模型能够基于形式化语言进行推理运算，进行自动化证明。

- 计算机科学：目前很多AI Scientist的概念和框架，其实是AI Computer Scientist，主要是自去年8月《The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery》发表之后，在相当长的一段时间内定义了这一方向的研究模式。

- 生物信息学：不仅诞生了像AlphaFold 3这样高度成功的科学数据大模型，而且在基于完整流程的蛋白质结构预测、药物发现等方向，也时常成为AI技术应用的领先阵地。

- 在物理操作占比较高的学科，智能化闭环流程具备挑战性：

- 医学：例如临床实践中的诊断、手术操作，以及实验室中的病理分析、细胞培养等，都需要大量的、精细的物理操作。

- 纳米材料学：新材料的合成、表征和性能测试等环节，也往往需要研究人员进行大量且复杂的物理实验操作。

综上所述，自动通用科学家（AGS）代表了AI赋能科学发现的远大前景，从辅助人类的工具到具备独立研究能力的伙伴乃至探索者。但是其发展仍在融入物理实验和现实交互的科研环节充满挑战。

未来，AGS的实现不仅依赖于模型自身认知与学习能力的突破，更需要一个能够连接虚拟与现实科研环节、囊括多样化工具与实验流程的跨学科生态系统，而他山正在为此铺垫与准备着...

**\**

**参考文献**

[1]Zhang, P. et al. Scaling laws in scientific discovery with AI and robot scientists. arXiv

preprint arXiv:2503.22444 (2025).

[2]Wang, C. et al. StarWhisper Telescope: Agent-Based Observation Assistant System to Approach AI Astrophysicist. *arXiv preprint* arXiv:2412.06412v2 (2024).

**\**

统筹：他山宣传部

内容：李瑀旸

编辑：葛庆宇

审核：郑博元

排版：李小瑞

\

![](https://mmbiz.qpic.cn/mmbiz_png/syYRVhHpyg7b8nAXAu1oYUVlU2vDgjCjRLMhYaiaxbZkw2COobSW0WEicsciayQ2xWQ0I6r3niciaSJYJc3saAk7akQ/640?wx_fmt=png&wxfrom=5&wx_lazy=1&wx_co=1)![]()![]()![]()![]()![]()![]()![]()

\

![](https://mmbiz.qpic.cn/mmbiz_png/KJ2eNqNdCVp0gFnOLOBrcghIwxRkBe3toeMHQYJ1TE5o3pVd1ETE69wQkz3KMYGtquNBRSCUAwyfEPictSNRnwA/640?wx_fmt=png)![]()![]()![]()![]()![]()![]()![]()

TA SHAN\

**中国科学院大学他山学科交叉创新协会以“打破学科壁垒，扩宽认知边界”为理念，致力于搭建一个大学生进行跨学科交流的平台，赋能未来领军科技人才成长，自下而上地促进学科交叉融合发展，为科教兴国战略、人才强国战略和创新驱动发展战略的实施贡献力量。**

**\**

长按下方二维码

关注“他山学科交叉”公众号

▼

![](https://mmbiz.qpic.cn/mmbiz_jpg/YfcILJIWTSicic874N41utGibpfc10x2dFoEKTr9JKMkBPGMcpjnDhpWcIWibcB86iaicL5utSpxM4z0YAsMAtUbBVWQ/640?wx_fmt=jpeg&from=appmsg)

---
*原文：[他山学科交叉](https://mp.weixin.qq.com/s/IdpNIBOBJlNN6Ys42LvdTw)*
