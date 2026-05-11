# 阿里云安全组配置说明

## 需要开放的安全组规则

### 入方向规则

| 协议 | 端口范围 | 授权对象 | 说明 |
|------|----------|----------|------|
| TCP | 80 | 0.0.0.0/0 | HTTP服务 |
| TCP | 443 | 0.0.0.0/0 | HTTPS服务（可选） |

> **注意**: 应用监听在8080端口，通过Nginx反向代理到80端口对外提供服务。

## 配置步骤

### 1. 登录阿里云ECS控制台

1. 访问 https://ecs.console.aliyun.com
2. 选择目标ECS实例
3. 点击 "安全组" -> "配置规则"

### 2. 添加安全组规则

1. 点击 "入方向" -> "快速添加"
2. 选择 HTTP(80) 端口
3. 授权对象填写 `0.0.0.0/0`
4. 点击 "确定"

### 3. 验证端口开放

```bash
# 在服务器上检查端口是否正常
curl -I http://localhost/health

# 从本地电脑测试公网访问
curl -I http://<您的公网IP>/
```

## 防火墙配置（如有）

如果服务器启用了firewalld：

```bash
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload
```

如果使用ufw：

```bash
sudo ufw allow 80/tcp
sudo ufw reload
```