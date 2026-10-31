import { useEffect, useState } from 'react'
import { Table, Button, Tag, Space, Modal, Form, Input, Select, DatePicker, message, InputNumber } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import api from '../api'

const healthColor: Record<string, string> = {
  green: 'green', yellow: 'gold', red: 'red', na: 'default',
}
const statusColor: Record<string, string> = {
  draft: 'default', applying: 'processing', active: 'green',
  suspended: 'orange', closed: 'blue', cancelled: 'red',
}

export default function Projects() {
  const navigate = useNavigate()
  const [data, setData] = useState<any[]>([])
  const [types, setTypes] = useState<any[]>([])
  const [depts, setDepts] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = () => {
    api.get('/projects').then((res: any) => setData(res.data || []))
  }

  useEffect(() => {
    load()
    api.get('/project-types').then((r: any) => setTypes(r.data || []))
    api.get('/depts').then((r: any) => setDepts(r.data || []))
    api.get('/users').then((r: any) => setUsers(r.data || []))
  }, [])

  const columns = [
    { title: '编号', dataIndex: 'code' },
    { title: '项目名称', dataIndex: 'name', render: (t: string, r: any) => <a onClick={() => navigate(`/projects/${r.id}`)}>{t}</a> },
    { title: '类型', dataIndex: 'type_name' },
    { title: 'PM', dataIndex: 'pm_name' },
    { title: '部门', dataIndex: 'dept_name' },
    { title: '进度', dataIndex: 'progress_pct', render: (v: number) => `${v}%` },
    { title: '健康度', dataIndex: 'health', render: (h: string) => <Tag color={healthColor[h]}>{h}</Tag> },
    { title: '状态', dataIndex: 'status', render: (s: string) => <Tag color={statusColor[s]}>{s}</Tag> },
    { title: '计划周期', dataIndex: 'plan_start', render: (_: any, r: any) => `${r.plan_start} ~ ${r.plan_end}` },
  ]

  const onCreate = async (values: any) => {
    const payload = {
      ...values,
      plan_start: values.plan_start.format('YYYY-MM-DD'),
      plan_end: values.plan_end.format('YYYY-MM-DD'),
    }
    await api.post('/projects', payload)
    message.success('项目创建成功')
    setOpen(false)
    form.resetFields()
    load()
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>新建项目</Button>
      </Space>
      <Table columns={columns} dataSource={data} rowKey="id" pagination={{ pageSize: 10 }} />

      <Modal title="新建项目" open={open} onCancel={() => setOpen(false)} onOk={() => form.submit()} width={700}>
        <Form form={form} layout="vertical" onFinish={onCreate}>
          <Form.Item name="name" label="项目名称" rules={[{ required: true }]}>
            <Input placeholder="请输入项目名称" />
          </Form.Item>
          <Form.Item name="type_id" label="项目类型" rules={[{ required: true }]}>
            <Select placeholder="请选择项目类型" options={types.map((t) => ({ value: t.id, label: t.name }))} />
          </Form.Item>
          <Form.Item name="pm_user_id" label="项目经理" rules={[{ required: true }]}>
            <Select placeholder="请选择 PM" showSearch optionFilterProp="label" options={users.map((u) => ({ value: u.id, label: `${u.name} (${u.employee_no})` }))} />
          </Form.Item>
          <Form.Item name="dept_id" label="归属部门" rules={[{ required: true }]}>
            <Select placeholder="请选择部门" options={depts.map((d) => ({ value: d.id, label: d.name }))} />
          </Form.Item>
          <Form.Item name="secrecy_level" label="密级" rules={[{ required: true }]} initialValue="internal">
            <Select options={[
              { value: 'public', label: '公开' },
              { value: 'internal', label: '内部' },
              { value: 'confidential', label: '机密' },
              { value: 'secret', label: '绝密' },
            ]} />
          </Form.Item>
          <Form.Item name="plan_start" label="计划开始" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="plan_end" label="计划结束" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
