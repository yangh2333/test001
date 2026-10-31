import { useEffect, useState } from 'react'
import { Select, Card, Button, Form, Input, message, Empty, Space, Tag } from 'antd'
import api from '../api'

export default function Weekly() {
  const [projects, setProjects] = useState<any[]>([])
  const [projectId, setProjectId] = useState<number | null>(null)
  const [report, setReport] = useState<any>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    api.get('/projects').then((r: any) => {
      const list = r.data || []
      setProjects(list)
    })
  }, [])

  useEffect(() => {
    if (projectId) {
      api.get(`/projects/${projectId}/weekly-reports/current`).then((r: any) => {
        setReport(r.data)
        form.setFieldsValue({ pm_comment: r.data.pm_comment, risk_supplement: r.data.risk_supplement })
      })
    }
  }, [projectId])

  const onSave = async (values: any) => {
    if (!report) return
    await api.patch(`/weekly-reports/${report.id}`, values)
    message.success('已保存补充内容')
  }

  const onPublish = async () => {
    if (!report) return
    await api.post(`/weekly-reports/${report.id}/publish`)
    message.success('周报已发布')
    setReport({ ...report, status: 'published' })
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <span>选择项目：</span>
        <Select
          style={{ width: 300 }}
          value={projectId}
          onChange={setProjectId}
          options={projects.map((p) => ({ value: p.id, label: p.name }))}
          placeholder="请选择项目"
        />
      </Space>

      {!report ? (
        <Empty description="请选择项目查看本周周报" />
      ) : (
        <Card title={`本周周报 (${report.week_start} ~ ${report.week_end})`} extra={<Tag color={report.status === 'published' ? 'green' : 'orange'}>{report.status}</Tag>}>
          <div style={{ marginBottom: 24 }}>
            <h4>系统自动汇总</h4>
            <p><strong>已完成任务：</strong>{(report.auto_content?.done_tasks || []).length} 项</p>
            <ul>
              {(report.auto_content?.done_tasks || []).map((t: any, i: number) => (
                <li key={i}>{t.name}</li>
              ))}
            </ul>
            <p><strong>进行中任务：</strong></p>
            <ul>
              {(report.auto_content?.progress_delta || []).map((t: any, i: number) => (
                <li key={i}>{t.name} - {t.progress}%</li>
              ))}
            </ul>
            <p><strong>下周计划：</strong></p>
            <ul>
              {(report.auto_content?.next_week || []).map((t: any, i: number) => (
                <li key={i}>{t.name}</li>
              ))}
            </ul>
          </div>

          {report.ai_summary && (
            <div style={{ marginBottom: 24 }}>
              <h4>AI 摘要</h4>
              <p style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>{report.ai_summary}</p>
            </div>
          )}

          <Form form={form} layout="vertical" onFinish={onSave}>
            <Form.Item name="pm_comment" label="PM 补充说明">
              <Input.TextArea rows={4} />
            </Form.Item>
            <Form.Item name="risk_supplement" label="风险补充">
              <Input.TextArea rows={3} />
            </Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">保存补充</Button>
              <Button onClick={onPublish} disabled={report.status === 'published'}>发布周报</Button>
            </Space>
          </Form>
        </Card>
      )}
    </div>
  )
}
