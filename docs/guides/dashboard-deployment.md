# Agent Dashboard 部署指南

## 开发环境部署

### 1. 启动后端服务

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
PYTHONPATH=. uvicorn examples.agent_dashboard_backend:app --reload --port 8000
```

### 2. 启动前端服务

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys/web-dashboard
pnpm dev
```

### 3. 访问界面

打开浏览器访问 `http://localhost:5173`

## 生产环境部署

### 前端构建

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys/web-dashboard
pnpm build
```

### 部署方式

1. 使用 Nginx 托管静态文件
2. 后端服务使用 Docker 容器化部署
