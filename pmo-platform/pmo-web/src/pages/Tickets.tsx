import { useEffect, useState } from 'react'
import { Table, Tag, Button, Space, Modal, Form, Input, Select, Radio, message, Tabs } from 'antd'
import api from '../api'

const statusColor: Record<string, string> = {
  pending: 'orange', accepted: 'blue', resolved: 'cyan',
  closed: 'green', rejected: 'red', escalated: 'volcano',
}
const typeColor: Record<string, string> = {
  resource: 'blue', support: 'green', decision: 'purple',
}

export default function Tickets() {
  const [data, setData] = useState<any[]>([])
  const [depts, setDepts] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState<any>(null)
  const [form] = Form.useForm()

  const load = (scope = 'all') => {
    api.get(`/tickets?scope=${scope}`).then((r: any) => setData(r.data || []))
  }

  useEffect(() => {
    load()
    api.get('/depts').then((r: any) => setDepts(r.data || []))
    api.get('/users').then((r: any) => setUsers(r.data || []))
  }, [])

  const columns = [
    { title: '工单号', dataIndex: 'code' },
    { title: '标题', dataIndex: 'title', render: (t: string, r: any) => <a onClick={() => setDetail(r)}>{t}</a> },
    { title: '类型', dataIndex: 'ticket_type', render: (t: string) => <Tag color={typeColor[t]}>{t}</Tag> },
    { title: '优先级', dataIndex: 'priority', render: (p: number) => <Tag color={p <= 2 ? 'red' : 'orange'}>P{p}</Tag> },
    { title: '发起人', dataIndex: 'requester_name' },
    { title: '目标部门', dataIndex: 'target_dept_name' },
    { title: 'SLA截止', dataIndex: 'sla_due_at' },
    { title: '状态', dataIndex: 'status', render: (s: string) => <Tag color={statusColor[s]}>{s}</Tag> },
  ]

  const onCreate = async (values: any) => {
    await api.post('/tickets', values)
    message.success('工单创建成功')
    setOpen(false)
    form.resetFields()
    load()
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={() => setOpen(true)}>发起工单</Button>
      </Space>

      <Tabs
        defaultActiveKey="all"
        onChange={(k) => load(k)}
        items={[
          { key: 'all', label: '全部工单' },
          { key: 'mine', label: '我的工单' },
          { key: 'dept', label: '本部门工单' },
        ]}
      />

      <Table columns={columns} dataSource={data} rowKey="id" size="small" pagination={{ pageSize: 10 }} />

      <Modal title="发起工单" open={open} onCancel={() => setOpen(false)} onOk={() => form.submit()} width={600}>
        <Form form={form} layout="vertical" onFinish={onCreate}>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="ticket_type" label="类型" rules={[{ required: true }]} initialValue="support">
            <Radio.Group>
              <Radio value="resource">资源申请</Radio>
              <Radio value="support">技术支持</Radio>
              <Radio value="decision">请决策</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item name="target_dept_id" label="目标部门" rules={[{ required: true }]}>
            <Select options={depts.map((d) => ({ value: d.id, label: d.name }))} />
          </Form.Item>
          <Form.Item name="target_user_id" label="指定处理人（可选）">
            <Select showSearch optionFilterProp="label" options={users.map((u) => ({ value: u.id, label: u.name }))} />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue={3}>
            <Select options={[1, 2, 3, 4, 5].map((p) => ({ value: p, label: `P${p}` }))} />
          </Form.Item>
          <Form.Item name="description" label="描述" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="工单详情" open={!!detail} onCancel={() => setDetail(null)} footer={null} width={700}>
        {detail && (
          <div>
            <h3>{detail.title}</h3>
            <p>工单号：{detail.code}</p>
            <p>类型：{detail.ticket_type} | 优先级：P{detail.priority}</p>
            <p>发起人：{detail.requester_name}</p>
            <p>目标部门：{detail.target_dept_name}</p>
            <p>状态：<Tag color={statusColor[detail.status]}>{detail.status}</Tag></p>
            <p>SLA 截止：{detail.sla_due_at}</p>
            <p>描述：{detail.description}</p>
            <Space>
              <Button onClick={() => { api.post(`/tickets/${detail.id}/accept`); message.success('已受理'); load(); setDetail(null) }}>受理</Button>
              <Button type="primary" onClick={() => { api.post(`/tickets/${detail.id}/resolve`); message.success('已解决'); load(); setDetail(null) }}>标记解决</Button>
            </Space>
          </div>
        )}
      </Modal>
    </div>
  )
}
