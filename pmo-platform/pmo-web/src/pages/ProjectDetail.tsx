import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Descriptions, Tag, Button, Space, Tabs, Table, Progress, Modal, Form, Input, Select, DatePicker, message } from 'antd'
import { ArrowLeftOutlined, BarChartOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api'

const healthColor: Record<string, string> = { green: 'green', yellow: 'gold', red: 'red', na: 'default' }

export default function ProjectDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState<any>(null)
  const [wbs, setWbs] = useState<any[]>([])
  const [tasks, setTasks] = useState<any[]>([])
  const [gates, setGates] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [taskOpen, setTaskOpen] = useState(false)
  const [form] = Form.useForm()

  const load = () => {
    api.get(`/projects/${id}`).then((r: any) => setProject(r.data))
    api.get(`/projects/${id}/wbs`).then((r: any) => setWbs(r.data || []))
    api.get(`/projects/${id}/tasks`).then((r: any) => setTasks(r.data || []))
    api.get(`/projects/${id}/gates`).then((r: any) => setGates(r.data || []))
  }

  useEffect(() => {
    load()
    api.get('/users').then((r: any) => setUsers(r.data || []))
  }, [id])

  if (!project) return null

  const taskColumns = [
    { title: '任务名称', dataIndex: 'name' },
    { title: '负责人', dataIndex: 'owner_name' },
    { title: '计划开始', dataIndex: 'plan_start' },
    { title: '计划结束', dataIndex: 'plan_end' },
    { title: '进度', dataIndex: 'progress_pct', render: (v: number) => <Progress percent={v} size="small" /> },
    { title: '状态', dataIndex: 'status', render: (s: string) => <Tag>{s}</Tag> },
    { title: '里程碑', dataIndex: 'is_milestone', render: (v: boolean) => v ? <Tag color="blue">里程碑</Tag> : null },
  ]

  const onCreateTask = async (values: any) => {
    await api.post(`/projects/${id}/tasks`, {
      ...values,
      plan_start: values.plan_start.format('YYYY-MM-DD'),
      plan_end: values.plan_end.format('YYYY-MM-DD'),
      project_id: Number(id),
    })
    message.success('任务创建成功')
    setTaskOpen(false)
    form.resetFields()
    load()
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/projects')}>返回</Button>
        <Button type="primary" icon={<BarChartOutlined />} onClick={() => navigate(`/gantt/${id}`)}>查看甘特图</Button>
      </Space>

      <Card title={project.name} style={{ marginBottom: 16 }}>
        <Descriptions column={3}>
          <Descriptions.Item label="项目编号">{project.code}</Descriptions.Item>
          <Descriptions.Item label="类型">{project.type_name}</Descriptions.Item>
          <Descriptions.Item label="PM">{project.pm_name}</Descriptions.Item>
          <Descriptions.Item label="部门">{project.dept_name}</Descriptions.Item>
          <Descriptions.Item label="密级"><Tag>{project.secrecy_level}</Tag></Descriptions.Item>
          <Descriptions.Item label="健康度"><Tag color={healthColor[project.health]}>{project.health}</Tag></Descriptions.Item>
          <Descriptions.Item label="计划周期">{project.plan_start} ~ {project.plan_end}</Descriptions.Item>
          <Descriptions.Item label="进度"><Progress percent={project.progress_pct} size="small" /></Descriptions.Item>
          <Descriptions.Item label="状态"><Tag>{project.status}</Tag></Descriptions.Item>
        </Descriptions>
      </Card>

      <Tabs
        defaultActiveKey="tasks"
        items={[
          {
            key: 'tasks',
            label: '任务列表',
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Button type="primary" onClick={() => setTaskOpen(true)}>新建任务</Button>
                </Space>
                <Table columns={taskColumns} dataSource={tasks} rowKey="id" size="small" pagination={{ pageSize: 10 }} />
              </>
            ),
          },
          {
            key: 'wbs',
            label: 'WBS 结构',
            children: (
              <Table
                dataSource={wbs}
                rowKey="id"
                size="small"
                pagination={false}
                columns={[
                  { title: '编码', dataIndex: 'code', width: 120 },
                  { title: '名称', dataIndex: 'name' },
                  { title: '层级', dataIndex: 'level', width: 80 },
                ]}
              />
            ),
          },
          {
            key: 'gates',
            label: '门禁评审',
            children: (
              <Table
                dataSource={gates}
                rowKey="id"
                size="small"
                pagination={false}
                columns={[
                  { title: '门禁名称', dataIndex: 'name' },
                  { title: '状态', dataIndex: 'status', render: (s: string) => <Tag>{s}</Tag> },
                  { title: '结论', dataIndex: 'decision' },
                  { title: '高危', dataIndex: 'is_high_risk', render: (v: boolean) => v ? <Tag color="red">高危</Tag> : null },
                  { title: '阻塞', dataIndex: 'blocked_flag', render: (v: boolean) => v ? <Tag color="red">阻塞</Tag> : null },
                ]}
              />
            ),
          },
          {
            key: 'stages',
            label: '阶段',
            children: (
              <Table
                dataSource={project.stages || []}
                rowKey="id"
                size="small"
                pagination={false}
                columns={[
                  { title: '阶段名称', dataIndex: 'name' },
                  { title: '状态', dataIndex: 'status', render: (s: string) => <Tag>{s}</Tag> },
                  { title: '计划开始', dataIndex: 'plan_start' },
                  { title: '计划结束', dataIndex: 'plan_end' },
                ]}
              />
            ),
          },
        ]}
      />

      <Modal title="新建任务" open={taskOpen} onCancel={() => setTaskOpen(false)} onOk={() => form.submit()} width={600}>
        <Form form={form} layout="vertical" onFinish={onCreateTask}>
          <Form.Item name="name" label="任务名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="owner_user_id" label="负责人" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={users.map((u) => ({ value: u.id, label: u.name }))} />
          </Form.Item>
          <Form.Item name="wbs_id" label="所属 WBS">
            <Select options={wbs.map((w) => ({ value: w.id, label: `${w.code} ${w.name}` }))} />
          </Form.Item>
          <Form.Item name="plan_start" label="计划开始" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="plan_end" label="计划结束" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue={3}>
            <Select options={[1, 2, 3, 4, 5].map((p) => ({ value: p, label: `P${p}` }))} />
          </Form.Item>
          <Form.Item name="is_milestone" label="里程碑" valuePropName="checked">
            <Select options={[{ value: false, label: '否' }, { value: true, label: '是' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
