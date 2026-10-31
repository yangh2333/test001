import { useState } from 'react'
import { Card, Form, Input, Button, Typography, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const { Title } = Typography

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { employee_no: string; password: string }) => {
    setLoading(true)
    try {
      const res: any = await api.post('/auth/login', values)
      setAuth(res.data.token, res.data.user)
      message.success('登录成功')
      navigate('/dashboard')
    } catch (e) {
      // error handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <Card style={{ width: 400, boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={3} style={{ marginBottom: 4 }}>PMO 运维管理平台</Title>
          <p style={{ color: '#999' }}>面向芯片研发全链条的项目协同平台</p>
        </div>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="employee_no" rules={[{ required: true, message: '请输入工号' }]}>
            <Input prefix={<UserOutlined />} placeholder="工号" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录
            </Button>
          </Form.Item>
        </Form>
        <p style={{ textAlign: 'center', color: '#bbb', fontSize: 12 }}>
          默认账号: admin / admin123
        </p>
      </Card>
    </div>
  )
}
