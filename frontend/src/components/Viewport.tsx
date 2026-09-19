import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { colormap, type ColormapName } from '../lib/colormap'
import type { MeshPayload } from '../lib/types'

export interface ViewportProps {
  mesh: MeshPayload | null
  values: number[] | null
  range: [number, number]          // normalised colour range, 0..1 of [min,max]
  min: number
  max: number
  unit: string
  cmap: ColormapName
  wireframe: boolean
  transparent: boolean
  clip: { on: boolean; axis: 'x' | 'y' | 'z'; position: number }
  hiddenParts: Set<number>
  deformScale: number
  viewCommand: { name: string; nonce: number } | null
  onProbe?: (p: { value: number; node: number; xyz: [number, number, number] }) => void
}

interface Ctx {
  renderer: THREE.WebGLRenderer
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  geometry: THREE.BufferGeometry
  material: THREE.MeshStandardMaterial
  mesh: THREE.Mesh
  plane: THREE.Plane
  target: THREE.Vector3
  spherical: { r: number; theta: number; phi: number }
  radius: number
  markers: THREE.Group
  base: Float32Array
  frame: number
}

/** WebGL result viewport: coloured surface, orbit/pan/zoom, section plane, probes. */
export default function Viewport(props: ViewportProps) {
  const holder = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const ctx = useRef<Ctx | null>(null)
  const [hover, setHover] = useState<{ x: number; y: number; text: string } | null>(null)

  // ---------------------------------------------------------------- set-up
  useEffect(() => {
    if (!canvas.current || !holder.current) return
    const renderer = new THREE.WebGLRenderer({ canvas: canvas.current, antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.localClippingEnabled = true
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 1e5)
    scene.add(new THREE.HemisphereLight(0xdfe9f2, 0x30404d, 0.9))
    const key = new THREE.DirectionalLight(0xffffff, 0.75)
    key.position.set(1, 1.6, 1.2)
    const fill = new THREE.DirectionalLight(0xffffff, 0.3)
    fill.position.set(-1.2, -0.4, -1)
    scene.add(key, fill)
    const geometry = new THREE.BufferGeometry()
    const material = new THREE.MeshStandardMaterial({
      vertexColors: true, metalness: 0.08, roughness: 0.72, side: THREE.DoubleSide,
    })
    const mesh = new THREE.Mesh(geometry, material)
    const markers = new THREE.Group()
    scene.add(mesh, markers)
    const state: Ctx = {
      renderer, scene, camera, geometry, material, mesh,
      plane: new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0),
      target: new THREE.Vector3(), spherical: { r: 3, theta: 0.9, phi: 1.05 },
      radius: 1, markers, base: new Float32Array(), frame: 0,
    }
    ctx.current = state

    const loop = () => {
      state.frame = requestAnimationFrame(loop)
      const { r, theta, phi } = state.spherical
      camera.position.set(
        state.target.x + r * Math.sin(phi) * Math.sin(theta),
        state.target.y + r * Math.cos(phi),
        state.target.z + r * Math.sin(phi) * Math.cos(theta),
      )
      camera.lookAt(state.target)
      renderer.render(scene, camera)
    }
    loop()

    const resize = () => {
      const rect = holder.current!.getBoundingClientRect()
      if (!rect.width || !rect.height) return
      renderer.setSize(rect.width, rect.height, false)
      camera.aspect = rect.width / rect.height
      camera.updateProjectionMatrix()
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(holder.current)

    return () => {
      cancelAnimationFrame(state.frame)
      ro.disconnect()
      geometry.dispose()
      material.dispose()
      renderer.dispose()
      ctx.current = null
    }
  }, [])

  // ------------------------------------------------------------ geometry
  useEffect(() => {
    const s = ctx.current
    if (!s || !props.mesh) return
    const { nodes, triangles } = props.mesh
    const positions = new Float32Array(nodes)
    s.base = Float32Array.from(positions)
    s.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    s.geometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(nodes.length), 3))
    s.geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(triangles), 1))
    s.geometry.computeVertexNormals()
    s.geometry.computeBoundingSphere()
    const sphere = s.geometry.boundingSphere!
    s.target.copy(sphere.center)
    s.radius = sphere.radius
    s.spherical.r = sphere.radius * 2.6
  }, [props.mesh])

  // -------------------------------------------------- colours + deformation
  useEffect(() => {
    const s = ctx.current
    if (!s || !props.mesh || !props.values) return
    const colors = s.geometry.getAttribute('color') as THREE.BufferAttribute
    const position = s.geometry.getAttribute('position') as THREE.BufferAttribute
    const span = props.max - props.min || 1
    const [lo, hi] = props.range
    const hidden = props.hiddenParts
    const partOf = props.mesh.part_ids
    // A vertex is dimmed when every triangle that uses it belongs to a hidden part.
    const visible = new Uint8Array(props.values.length).fill(hidden.size ? 0 : 1)
    if (hidden.size) {
      const tris = props.mesh.triangles
      for (let t = 0; t < partOf.length; t++) {
        if (hidden.has(partOf[t])) continue
        visible[tris[t * 3]] = 1
        visible[tris[t * 3 + 1]] = 1
        visible[tris[t * 3 + 2]] = 1
      }
    }
    for (let i = 0; i < props.values.length; i++) {
      const norm = (props.values[i] - props.min) / span
      let r: number, g: number, b: number
      if (!visible[i]) {
        ;[r, g, b] = [40, 48, 55]
      } else if (norm < lo || norm > hi) {
        ;[r, g, b] = [96, 108, 118]
      } else {
        ;[r, g, b] = colormap(props.cmap, (norm - lo) / (hi - lo || 1))
      }
      colors.setXYZ(i, r / 255, g / 255, b / 255)
      if (props.deformScale > 0) {
        const f = Math.min(1, Math.max(0, norm)) * props.deformScale * s.radius * 0.02
        position.setXYZ(i, s.base[i * 3], s.base[i * 3 + 1] - f, s.base[i * 3 + 2])
      } else {
        position.setXYZ(i, s.base[i * 3], s.base[i * 3 + 1], s.base[i * 3 + 2])
      }
    }
    colors.needsUpdate = true
    position.needsUpdate = true
    s.geometry.computeVertexNormals()
  }, [props.values, props.range, props.cmap, props.min, props.max, props.hiddenParts,
      props.deformScale, props.mesh])

  // ---------------------------------------------------------------- style
  useEffect(() => {
    const s = ctx.current
    if (!s || !props.mesh) return
    s.material.wireframe = props.wireframe
    s.material.transparent = props.transparent
    s.material.opacity = props.transparent ? 0.45 : 1
    const { min, max } = props.mesh.bounds
    const axis = props.clip.axis
    const i = axis === 'x' ? 0 : axis === 'y' ? 1 : 2
    s.plane.normal.set(i === 0 ? -1 : 0, i === 1 ? -1 : 0, i === 2 ? -1 : 0)
    s.plane.constant = min[i] + (max[i] - min[i]) * props.clip.position
    s.material.clippingPlanes = props.clip.on ? [s.plane] : []
    s.material.needsUpdate = true
  }, [props.wireframe, props.transparent, props.clip, props.mesh])

  // -------------------------------------------------------- view commands
  useEffect(() => {
    const s = ctx.current
    if (!s || !props.viewCommand) return
    const presets: Record<string, [number, number]> = {
      iso: [0.9, 1.05], front: [0, 1.5708], top: [0, 0.01], right: [1.5708, 1.5708], left: [-1.5708, 1.5708],
    }
    if (props.viewCommand.name === 'fit') {
      s.geometry.computeBoundingSphere()
      const sphere = s.geometry.boundingSphere!
      s.target.copy(sphere.center)
      s.spherical.r = sphere.radius * 2.6
    } else if (props.viewCommand.name === 'clear') {
      s.markers.clear()
    } else {
      const p = presets[props.viewCommand.name]
      if (p) {
        s.spherical.theta = p[0]
        s.spherical.phi = p[1]
      }
    }
  }, [props.viewCommand])

  // ------------------------------------------------------------ interaction
  useEffect(() => {
    const el = canvas.current
    const s = ctx.current
    if (!el || !s) return
    let drag: { x: number; y: number; pan: boolean; moved: number } | null = null

    const pick = (e: PointerEvent) => {
      const rect = el.getBoundingClientRect()
      const ray = new THREE.Raycaster()
      ray.setFromCamera(new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1,
      ), s.camera)
      return ray.intersectObject(s.mesh, false)[0]
    }
    const nearestVertex = (hit: THREE.Intersection) => {
      const pos = s.geometry.getAttribute('position') as THREE.BufferAttribute
      const face = hit.face!
      let best = face.a
      let bestD = Infinity
      for (const idx of [face.a, face.b, face.c]) {
        const d = hit.point.distanceToSquared(
          new THREE.Vector3(pos.getX(idx), pos.getY(idx), pos.getZ(idx)))
        if (d < bestD) { bestD = d; best = idx }
      }
      return best
    }

    const down = (e: PointerEvent) => {
      el.setPointerCapture(e.pointerId)
      drag = { x: e.clientX, y: e.clientY, pan: e.button === 2 || e.shiftKey, moved: 0 }
    }
    const move = (e: PointerEvent) => {
      if (!drag) {
        const hit = pick(e)
        if (!hit || !props.values) { setHover(null); return }
        const idx = nearestVertex(hit)
        const rect = el.getBoundingClientRect()
        setHover({
          x: e.clientX - rect.left + 12, y: e.clientY - rect.top + 12,
          text: `${props.values[idx].toFixed(3)} ${props.unit}`,
        })
        return
      }
      const dx = e.clientX - drag.x
      const dy = e.clientY - drag.y
      drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy)
      if (drag.pan) {
        const f = s.spherical.r * 0.0018
        const right = new THREE.Vector3().setFromMatrixColumn(s.camera.matrix, 0)
        const up = new THREE.Vector3().setFromMatrixColumn(s.camera.matrix, 1)
        s.target.addScaledVector(right, -dx * f).addScaledVector(up, dy * f)
      } else {
        s.spherical.theta -= dx * 0.008
        s.spherical.phi = Math.min(Math.PI - 0.05, Math.max(0.05, s.spherical.phi - dy * 0.008))
      }
    }
    const up = (e: PointerEvent) => {
      if (drag && drag.moved < 4 && props.values && props.onProbe) {
        const hit = pick(e)
        if (hit) {
          const idx = nearestVertex(hit)
          const geo = new THREE.SphereGeometry(s.radius * 0.016, 12, 10)
          const marker = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: 0xffffff }))
          marker.position.copy(hit.point)
          s.markers.add(marker)
          props.onProbe({
            value: props.values[idx], node: idx + 1,
            xyz: [hit.point.x, hit.point.y, hit.point.z],
          })
        }
      }
      drag = null
    }
    const wheel = (e: WheelEvent) => {
      e.preventDefault()
      s.spherical.r = Math.min(s.radius * 14, Math.max(s.radius * 0.3,
        s.spherical.r * (1 + Math.sign(e.deltaY) * 0.11)))
    }
    const menu = (e: Event) => e.preventDefault()

    el.addEventListener('pointerdown', down)
    el.addEventListener('pointermove', move)
    el.addEventListener('pointerup', up)
    el.addEventListener('wheel', wheel, { passive: false })
    el.addEventListener('contextmenu', menu)
    return () => {
      el.removeEventListener('pointerdown', down)
      el.removeEventListener('pointermove', move)
      el.removeEventListener('pointerup', up)
      el.removeEventListener('wheel', wheel)
      el.removeEventListener('contextmenu', menu)
    }
  }, [props.values, props.unit, props.onProbe])

  return (
    <div className="vpwrap" ref={holder}>
      <canvas ref={canvas} id="gl" />
      {hover && (
        <div className="probe-tip" style={{ display: 'block', left: hover.x, top: hover.y }}>
          {hover.text}
        </div>
      )}
      <div className="demo-flag">sample data</div>
    </div>
  )
}
