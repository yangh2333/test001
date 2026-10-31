import { useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Space, Tag } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import api from '../api'

// frappe-gantt 类型声明
declare global {
  interface Window {
    Gantt: any
  }
}

export default function Gantt() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const containerRef = useRef<HTMLDivElement>(null)
  const ganttRef = useRef<any>(null)

  useEffect(() => {
    let Gantt: any
    const init = async () => {
      // 动态加载 frappe-gantt 的 CSS 和 JS
      const cssId = 'frappe-gantt-css'
      if (!document.getElementById(cssId)) {
        const link = document.createElement('link')
        link.id = cssId
        link.rel = 'stylesheet'
        link.href = 'https://unpkg.com/frappe-gantt@0.6.1/dist/frappe-gantt.css'
        document.head.appendChild(link)
      }
      const mod = await import('frappe-gantt')
      Gantt = mod.default
      loadGantt(Gantt)
    }
    init()
  }, [projectId])

  const loadGantt = async (Gantt: any) => {
    if (!containerRef.current) return
    const res: any = await api.get(`/projects/${projectId}/gantt`)
    const tasks = res.data.tasks.map((t: any) => ({
      id: t.id,
      name: t.name,
      start: t.start,
      end: t.end,
      progress: t.progress,
      dependencies: t.dependencies || '',
      custom_class: t.custom_class || '',
    }))
    if (ganttRef.current) {
      ganttRef.current.destroy()
    }
    ganttRef.current = new Gantt(containerRef.current, tasks, {
      header_height: 50,
      column_width: 30,
      step: 24,
      view_modes: ['Quarter Day', 'Half Day', 'Day', 'Week', 'Month'],
      bar_height: 20,
      bar_corner_radius: 3,
      arrow_curve: 5,
      padding: 18,
    })
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
        <span style={{ marginLeft: 16 }}>
          <Tag color="red">红色 = 关键路径</Tag>
        </span>
      </Space>
      <Card>
        <div ref={containerRef} className="gantt-container" style={{ minHeight: 400 }} />
      </Card>
    </div>
  )
}
