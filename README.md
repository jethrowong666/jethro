# jethro

好物分享。目前收录的是 Claude Code 插件，这个仓库本身就是一个插件市场。

Good stuff worth sharing. For now: Claude Code plugins. This repository is a plugin marketplace.

## 插件 / Plugins

| 插件 | 说明 |
|---|---|
| [project-relay](plugins/project-relay/) | 项目接力：每个项目一张 `PROJECT.md` 项目卡，换会话、换账号、换电脑都能接着干；一句话重建左侧项目会话。<br>Pick up any project where the last session left off, across sessions, accounts, machines and AI tools. |

## 安装 / Install

最简单：在 Claude 桌面 App 的 Code 页发一句话。
The easy way: tell Claude (desktop app, Code tab):

> 安装 https://github.com/jethrowong666/jethro 里的 project-relay 并恢复我的项目
>
> Install project-relay from https://github.com/jethrowong666/jethro and restore my projects

手动安装 / Manually:
```
/plugin marketplace add jethrowong666/jethro
/plugin install project-relay@jethro
```

## License
MIT
