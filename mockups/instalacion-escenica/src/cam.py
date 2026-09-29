import numpy as np
from scipy.optimize import least_squares
W,H=1280,960
def rot(yaw,pitch,roll):
    cy,sy=np.cos(yaw),np.sin(yaw); cp,sp=np.cos(pitch),np.sin(pitch); cr,sr=np.cos(roll),np.sin(roll)
    Ry=np.array([[cy,0,-sy],[0,1,0],[sy,0,cy]])   # yaw: positive turns camera to the right (+X)
    Rx=np.array([[1,0,0],[0,cp,-sp],[0,sp,cp]])   # pitch: positive looks up
    Rz=np.array([[cr,-sr,0],[sr,cr,0],[0,0,1]])
    return Rz@Rx@Ry
class Cam:
    def __init__(s,f,C,yaw,pitch,roll,cx=W/2,cy=H/2):
        s.f=f; s.C=np.array(C,float); s.R=rot(yaw,pitch,roll); s.cx=cx; s.cy=cy
        s.params=(f,tuple(C),yaw,pitch,roll)
    def cam(s,P):
        P=np.atleast_2d(np.asarray(P,float))
        return (s.R@(P-s.C).T).T
    def project(s,P):
        Pc=s.cam(P)
        x=s.cx+s.f*Pc[:,0]/Pc[:,2]; y=s.cy-s.f*Pc[:,1]/Pc[:,2]
        return np.stack([x,y],1)
    def ray(s,x,y):
        d=np.array([(x-s.cx)/s.f, -(y-s.cy)/s.f, 1.0])
        return s.R.T@d
    def floor(s,x,y,h=0.0):
        d=s.ray(x,y); t=(h-s.C[1])/d[1]; return s.C+t*d
    def plane_z(s,x,y,z):
        d=s.ray(x,y); t=(z-s.C[2])/d[2]; return s.C+t*d
def fit(obs, x0, extra_fn=None, fixed={}):
    # obs: list of (fun(params)->3D point, (x,y))
    names=['f','cx','cy','cz','yaw','pitch','roll','a']
    def unpack(p):
        d=dict(zip(names,p)); d.update(fixed); return d
    def res(p):
        d=unpack(p)
        c=Cam(d['f'],[d['cx'],d['cy'],d['cz']],d['yaw'],d['pitch'],d['roll'])
        r=[]
        for fn,(u,v),*w in obs:
            P=fn(d); q=c.project(P)[0]; wt=w[0] if w else 1
            r+= [wt*(q[0]-u), wt*(q[1]-v)]
        return np.array(r)
    sol=least_squares(res,x0)
    d=unpack(sol.x)
    return d, res(sol.x).reshape(-1,2)
