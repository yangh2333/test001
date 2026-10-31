import { useEffect, useState } from 'react'
import { List, Tag, Button, Card, Badge, Empty, Space } from 'antd'
import { CheckCircleOutlined } from '@ant-design/icons'
import api from '../api'

const kindLabel: Record<string, string> = {
  task: '任务', approval: '审批', review: '评审', risk: '风险',
  ticket: '工单', handoff: '交接', meeting: '会议决议', sync_conflict: '同步冲突',
}
const kindColor: Record<string, string> = {
  task: 'blue', approval: 'red', review: 'purple', risk: 'orange',
  ticket: 'cyan', handoff: 'green', meeting: 'magenta', sync_conflict: 'gold',
}

export default function Todos() {
  const [data, setData] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)

  const load = () => {
    api.get('/todos').then((r: any) => setData(r.data || []))
    api.get('/todos/stats').then((r: any) => setStats(r.data))
  }

  useEffect(() => { load() }, [])

  const handleDone = (id: number) => {
    api.patch(`/todos/${id}?status=done`).then(() => load())
  }

  return (
    <div>
      {stats && (
        <Card style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 16, marginRight: 24 }}>待办总数：<strong>{stats.total}</strong></span>
          {Object.entries(stats.by_kind || {}).map(([k, v]) => (
            <Tag key={k} color={kindColor[k]} style={{ marginRight: 12 }}>{kindLabel[k]}: {v as number}</Tag>
          ))}
        </Card>
      )}

      <Card title="待办列表">
        {data.length === 0 ? (
          <Empty description="暂无待办" />
        ) : (
          <List
            dataSource={data}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button type="primary" size="small" icon={<CheckCircleOutlined />} onClick={() => handleDone(item.id)}>完成</Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color={kindColor[item.kind]}>{kindLabel[item.kind]}</Tag>
                      <span>{item.title}</span>
                    </Space>
                  }
                  description={item.due_at ? `截止：${item.due_at}` : '无截止时间'}
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  )
}
