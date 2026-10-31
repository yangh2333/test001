import { useEffect, useState } from 'react'
import { Table, Tag, Select, Space, Progress } from 'antd'
import api from '../api'

const statusColor: Record<string, string> = {
  not_started: 'default', in_progress: 'processing', blocked: 'red',
  done: 'green', cancelled: 'default',
}

export default function Tasks() {
  const [projects, setProjects] = useState<any[]>([])
  const [tasks, setTasks] = useState<any[]>([])
  const [projectId, setProjectId] = useState<number | null>(null)

  useEffect(() => {
    api.get('/projects').then((r: any) => {
      const list = r.data || []
      setProjects(list)
      if (list.length > 0) {
        setProjectId(list[0].id)
      }
    })
  }, [])

  useEffect(() => {
    if (projectId) {
      api.get(`/projects/${projectId}/tasks`).then((r: any) => setTasks(r.data || []))
    }
  }, [projectId])

  const columns = [
    { title: '任务名称', dataIndex: 'name' },
    { title: '负责人', dataIndex: 'owner_name' },
    { title: '计划开始', dataIndex: 'plan_start' },
    { title: '计划结束', dataIndex: 'plan_end' },
    { title: '进度', dataIndex: 'progress_pct', render: (v: number) => <Progress percent={v} size="small" /> },
    { title: '状态', dataIndex: 'status', render: (s: string) => <Tag color={statusColor[s]}>{s}</Tag> },
    { title: '优先级', dataIndex: 'priority', render: (p: number) => <Tag color={p <= 2 ? 'red' : p <= 3 ? 'orange' : 'blue'}>P{p}</Tag> },
    { title: '里程碑', dataIndex: 'is_milestone', render: (v: boolean) => v ? <Tag color="purple">里程碑</Tag> : null },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <span>选择项目：</span>
        <Select
          style={{ width: 300 }}
          value={projectId}
          onChange={setProjectId}
          options={projects.map((p) => ({ value: p.id, label: p.name }))}
        />
      </Space>
      <Table columns={columns} dataSource={tasks} rowKey="id" size="small" pagination={{ pageSize: 15 }} />
    </div>
  )
}
