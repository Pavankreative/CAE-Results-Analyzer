"""Small procedural surface-mesh builders used by the sample generator.

Each builder returns (nodes, triangles) with triangles indexing into nodes.
Meshes are surface skins: enough to post-process and render, which is what the
sample datasets need.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np


def _grid(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    uu, vv = np.meshgrid(u, v, indexing="ij")
    return np.stack([uu.ravel(), vv.ravel()], axis=1)


def _quad_tris(nu: int, nv: int, offset: int = 0) -> np.ndarray:
    tris: List[List[int]] = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = offset + i * nv + j
            b = a + nv
            tris.append([a, b, a + 1])
            tris.append([b, b + 1, a + 1])
    return np.asarray(tris, dtype=np.int32)


def box_surface(size, center=(0, 0, 0), seg=(6, 6, 6)) -> Tuple[np.ndarray, np.ndarray]:
    sx, sy, sz = (s / 2 for s in size)
    cx, cy, cz = center
    nx, ny, nz = seg
    nodes: List[np.ndarray] = []
    tris: List[np.ndarray] = []
    off = 0
    faces = [
        (np.linspace(-sx, sx, nx), np.linspace(-sy, sy, ny), 2, sz),
        (np.linspace(-sx, sx, nx), np.linspace(-sy, sy, ny), 2, -sz),
        (np.linspace(-sx, sx, nx), np.linspace(-sz, sz, nz), 1, sy),
        (np.linspace(-sx, sx, nx), np.linspace(-sz, sz, nz), 1, -sy),
        (np.linspace(-sy, sy, ny), np.linspace(-sz, sz, nz), 0, sx),
        (np.linspace(-sy, sy, ny), np.linspace(-sz, sz, nz), 0, -sx),
    ]
    for a, b, axis, const in faces:
        g = _grid(a, b)
        pts = np.zeros((len(g), 3))
        free = [i for i in range(3) if i != axis]
        pts[:, free[0]] = g[:, 0]
        pts[:, free[1]] = g[:, 1]
        pts[:, axis] = const
        pts += np.asarray([cx, cy, cz])
        nodes.append(pts)
        tris.append(_quad_tris(len(a), len(b), off))
        off += len(pts)
    return np.vstack(nodes), np.vstack(tris)


def ellipsoid_surface(radii, center=(0, 0, 0), nu=40, nv=24,
                      v_range=(0.0, np.pi)) -> Tuple[np.ndarray, np.ndarray]:
    u = np.linspace(0, 2 * np.pi, nu)
    v = np.linspace(v_range[0], v_range[1], nv)
    uu, vv = np.meshgrid(u, v, indexing="ij")
    x = radii[0] * np.sin(vv) * np.cos(uu)
    y = radii[1] * np.cos(vv)
    z = radii[2] * np.sin(vv) * np.sin(uu)
    nodes = np.stack([x.ravel(), y.ravel(), z.ravel()], axis=1) + np.asarray(center)
    return nodes, _quad_tris(nu, nv)


def cylinder_surface(radius, height, center=(0, 0, 0), axis="y", nu=28, nv=8
                     ) -> Tuple[np.ndarray, np.ndarray]:
    u = np.linspace(0, 2 * np.pi, nu)
    h = np.linspace(-height / 2, height / 2, nv)
    uu, hh = np.meshgrid(u, h, indexing="ij")
    a = radius * np.cos(uu)
    b = radius * np.sin(uu)
    if axis == "y":
        pts = np.stack([a.ravel(), hh.ravel(), b.ravel()], axis=1)
    elif axis == "x":
        pts = np.stack([hh.ravel(), a.ravel(), b.ravel()], axis=1)
    else:
        pts = np.stack([a.ravel(), b.ravel(), hh.ravel()], axis=1)
    return pts + np.asarray(center), _quad_tris(nu, nv)


def merge(parts: List[Tuple[str, np.ndarray, np.ndarray]]):
    """Merge named (nodes, triangles) pairs into one mesh with part ids."""
    nodes: List[np.ndarray] = []
    tris: List[np.ndarray] = []
    part_ids: List[np.ndarray] = []
    names: List[str] = []
    offset = 0
    for i, (name, n, t) in enumerate(parts):
        nodes.append(n)
        tris.append(t + offset)
        part_ids.append(np.full(len(t), i, dtype=np.int32))
        names.append(name)
        offset += len(n)
    return (np.vstack(nodes), np.vstack(tris), np.concatenate(part_ids), names)
