import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Tag, List, Badge } from 'antd'
import {
  ProjectOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import api from '../api'

const healthColor: Record<string, string> = {
  green: 'green',
  yellow: 'gold',
  red: 'red',
  na: 'default',
}

export default function Dashboard() {
  const [data, setData] = useState<any>(null)
  const [projects, setProjects] = useState<any[]>([])

  useEffect(() => {
    api.get('/dashboard/pm').then((res: any) => setData(res.data))
    api.get('/projects').then((res: any) => setProjects(res.data || []))
  }, [])

  if (!data) return null

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>驾驶舱</h2>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="我的项目" value={data.projects_count} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="待办事项" value={data.my_todos} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="阻塞任务" value={data.blocked_tasks} prefix={<WarningOutlined />} valueStyle={{ color: data.blocked_tasks > 0 ? '#cf1322' : undefined }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="超期工单" value={data.overdue_tickets} prefix={<ClockCircleOutlined />} valueStyle={{ color: data.overdue_tickets > 0 ? '#cf1322' : undefined }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="项目健康度分布">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="健康" value={data.health_distribution.green || 0} valueStyle={{ color: '#52c41a' }} />
              </Col>
              <Col span={6}>
                <Statistic title="预警" value={data.health_distribution.yellow || 0} valueStyle={{ color: '#faad14' }} />
              </Col>
              <Col span={6}>
                <Statistic title="异常" value={data.health_distribution.red || 0} valueStyle={{ color: '#cf1322' }} />
              </Col>
              <Col span={6}>
                <Statistic title="未评估" value={data.health_distribution.na || 0} />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="阻塞的门禁" extra={<Tag color="red">{data.blocked_gates}</Tag>}>
            {data.blocked_gates === 0 ? (
              <p style={{ color: '#999', textAlign: 'center', padding: 20 }}>暂无阻塞门禁</p>
            ) : (
              <p style={{ textAlign: 'center', padding: 20 }}>有 {data.blocked_gates} 个门禁未通过，请及时处理</p>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="我的项目列表" style={{ marginTop: 16 }}>
        <List
          dataSource={projects}
          renderItem={(p: any) => (
            <List.Item
              actions={[
                <Tag color={healthColor[p.health] || 'default'} key="health">
                  {p.health === 'green' ? '健康' : p.health === 'yellow' ? '预警' : p.health === 'red' ? '异常' : '未评估'}
                </Tag>,
                <span key="progress">进度 {p.progress_pct}%</span>,
              ]}
            >
              <List.Item.Meta
                title={<a href={`#/projects/${p.id}`}>{p.name}</a>}
                description={`${p.code} · ${p.type_name} · PM: ${p.pm_name} · ${p.plan_start} ~ ${p.plan_end}`}
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  )
}
