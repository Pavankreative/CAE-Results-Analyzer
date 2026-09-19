import { useState } from 'react'
import type { AppContext } from '../App'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { DOMAIN_VIEW } from '../lib/nav'
import { ErrorNote, KeyValues, Loading, Slab } from '../components/Primitives'

export default function Projects({ ctx }: { ctx: AppContext }) {
  const [name, setName] = useState('')
  const [picked, setPicked] = useState<string[]>([])
  const projects = useAsync(async () => {
    const list = await api.projects()
    return Promise.all(list.map((p) => api.project(p.id)))
  }, [])

  if (projects.error) return <ErrorNote error={projects.error} />
  if (!projects.data) return <Loading what="projects" />

  const create = async () => {
    if (!name.trim()) { ctx.toast('Give the project a name first'); return }
    await api.createProject({ name, simulation_ids: picked, description: 'Created in the application' })
    setName(''); setPicked([]); projects.reload(); ctx.toast('Project created')
  }
  const remove = async (id: string) => {
    await api.deleteProject(id); projects.reload(); ctx.toast('Project deleted')
  }

  return (
    <div className="scroll">
      <div className="vhead"><h1>Projects</h1>
        <p>A project groups simulations, their result sets and the reports built from them.</p></div>
      <div className="sub">Projects are stored as JSON documents under <code>data/projects</code>.</div>

      <Slab title="New project" style={{ marginBottom: 16 }}>
        <div className="body" style={{ display: 'grid', gap: 10 }}>
          <input type="text" placeholder="Project name" value={name}
                 onChange={(e) => setName(e.target.value)} />
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {ctx.simulations.map((s) => (
              <label className="chk" key={s.id} style={{ paddingLeft: 0 }}>
                <input type="checkbox" checked={picked.includes(s.id)}
                       onChange={(e) => setPicked(e.target.checked
                         ? [...picked, s.id] : picked.filter((x) => x !== s.id))} />
                {s.name}
              </label>
            ))}
          </div>
          <div><button className="btn primary" onClick={create}>Create project</button></div>
        </div>
      </Slab>

      <div className="grid g2">
        {projects.data.map((p) => (
          <Slab key={p.id} title={p.name}
                right={<span className="num" style={{ fontSize: 11, color: 'var(--ink-3)' }}>{p.id}</span>}>
            <div className="body">
              <p style={{ color: 'var(--ink-2)', fontSize: 12.5, margin: '0 0 10px' }}>
                {p.description || 'No description.'}
              </p>
              <KeyValues rows={[
                ['Owner', p.owner || '—'],
                ['Created', p.created || '—'],
                ['Simulations', p.simulation_ids.length],
              ]} />
              <div style={{ display: 'flex', gap: 7, marginTop: 11, flexWrap: 'wrap' }}>
                {(p.simulations ?? []).map((s) => (
                  <button key={s.id} className="btn sm primary"
                          onClick={() => ctx.go(DOMAIN_VIEW[s.domain] ?? 'simulations', s.id)}>
                    Open {s.domain}
                  </button>
                ))}
                <button className="btn sm" onClick={() => remove(p.id)}>Delete</button>
              </div>
            </div>
          </Slab>
        ))}
      </div>
    </div>
  )
}
