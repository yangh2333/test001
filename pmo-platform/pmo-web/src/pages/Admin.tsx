import { useEffect, useState } from 'react'
import { Tabs, Table, Button, Modal, Form, Input, Select, message, Tag } from 'antd'
import api from '../api'

export default function Admin() {
  const [roles, setRoles] = useState<any[]>([])
  const [bindings, setBindings] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [depts, setDepts] = useState<any[]>([])
  const [dicts, setDicts] = useState<any[]>([])
  const [audit, setAudit] = useState<any[]>([])
  const [userOpen, setUserOpen] = useState(false)
  const [bindingOpen, setBindingOpen] = useState(false)
  const [form] = Form.useForm()
  const [bindingForm] = Form.useForm()

  const loadAll = () => {
    api.get('/admin/roles').then((r: any) => setRoles(r.data || []))
    api.get('/admin/role-bindings').then((r: any) => setBindings(r.data || []))
    api.get('/users').then((r: any) => setUsers(r.data || []))
    api.get('/depts').then((r: any) => setDepts(r.data || []))
    api.get('/admin/dictionaries').then((r: any) => setDicts(r.data || []))
    api.get('/admin/audit-logs').then((r: any) => setAudit(r.data || []))
  }

  useEffect(() => { loadAll() }, [])

  const onCreateUser = async (values: any) => {
    await api.post('/admin/users', values)
    message.success('用户创建成功')
    setUserOpen(false)
    form.resetFields()
    loadAll()
  }

  const onCreateBinding = async (values: any) => {
    await api.post('/admin/role-bindings', values)
    message.success('授权成功')
    setBindingOpen(false)
    bindingForm.resetFields()
    loadAll()
  }

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>管理后台</h2>
      <Tabs
        items={[
          {
            key: 'users',
            label: '用户管理',
            children: (
              <>
                <Button type="primary" style={{ marginBottom: 16 }} onClick={() => setUserOpen(true)}>新建用户</Button>
                <Table
                  dataSource={users}
                  rowKey="id"
                  size="small"
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { title: '工号', dataIndex: 'employee_no' },
                    { title: '姓名', dataIndex: 'name' },
                    { title: '邮箱', dataIndex: 'email' },
                    { title: '部门', dataIndex: 'dept_name' },
                    { title: '岗位', dataIndex: 'title' },
                    { title: '角色', dataIndex: 'roles', render: (r: string[]) => (r || []).map((x) => <Tag key={x}>{x}</Tag>) },
                    { title: '状态', dataIndex: 'status', render: (s: string) => <Tag color={s === 'active' ? 'green' : 'red'}>{s}</Tag> },
                  ]}
                />
              </>
            ),
          },
          {
            key: 'roles',
            label: '角色授权',
            children: (
              <>
                <Button type="primary" style={{ marginBottom: 16 }} onClick={() => setBindingOpen(true)}>新增授权</Button>
                <Table
                  dataSource={bindings}
                  rowKey="id"
                  size="small"
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { title: '用户', dataIndex: 'user_name' },
                    { title: '角色', dataIndex: 'role_name' },
                    { title: '角色编码', dataIndex: 'role_code' },
                    { title: '到期时间', dataIndex: 'expires_at' },
                    {
                      title: '操作',
                      render: (_: any, r: any) => (
                        <Button size="small" danger onClick={async () => { await api.delete(`/admin/role-bindings/${r.id}`); message.success('已回收'); loadAll() }}>回收</Button>
                      ),
                    },
                  ]}
                />
              </>
            ),
          },
          {
            key: 'dicts',
            label: '字典管理',
            children: (
              <Table
                dataSource={dicts}
                rowKey="id"
                size="small"
                pagination={{ pageSize: 15 }}
                columns={[
                  { title: '分类', dataIndex: 'category' },
                  { title: '编码', dataIndex: 'code' },
                  { title: '名称', dataIndex: 'name' },
                  { title: '排序', dataIndex: 'sort_order' },
                ]}
              />
            ),
          },
          {
            key: 'audit',
            label: '审计日志',
            children: (
              <Table
                dataSource={audit}
                rowKey="id"
                size="small"
                pagination={{ pageSize: 15 }}
                columns={[
                  { title: '操作', dataIndex: 'action' },
                  { title: '对象类型', dataIndex: 'object_type' },
                  { title: '对象ID', dataIndex: 'object_id' },
                  { title: '操作者ID', dataIndex: 'actor_user_id' },
                  { title: '时间', dataIndex: 'created_at' },
                ]}
              />
            ),
          },
        ]}
      />

      <Modal title="新建用户" open={userOpen} onCancel={() => setUserOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={onCreateUser}>
          <Form.Item name="employee_no" label="工号" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="dept_id" label="部门">
            <Select options={depts.map((d) => ({ value: d.id, label: d.name }))} />
          </Form.Item>
          <Form.Item name="title" label="岗位">
            <Input />
          </Form.Item>
          <Form.Item name="password" label="初始密码" initialValue="123456">
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="新增授权" open={bindingOpen} onCancel={() => setBindingOpen(false)} onOk={() => bindingForm.submit()}>
        <Form form={bindingForm} layout="vertical" onFinish={onCreateBinding}>
          <Form.Item name="user_id" label="用户" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={users.map((u) => ({ value: u.id, label: u.name }))} />
          </Form.Item>
          <Form.Item name="role_id" label="角色" rules={[{ required: true }]}>
            <Select options={roles.map((r) => ({ value: r.id, label: r.name }))} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
