# AUTOGENERATED! DO NOT EDIT! File to edit: ../01_calc.ipynb.

# %% auto 0
__all__ = ['convert_q_to_Q', 'sort_1dim', 'sort_2dim', 'calc_bulk_values']

# %% ../01_calc.ipynb 2
import numpy as np
import xarray as xr
from tqdm import tqdm
import time

# %% ../01_calc.ipynb 3
def convert_q_to_Q(var_q, q, var_q2 = None):
    """Converts transport per coordinate class `q` to the integrated transport `Q` with the respective coordinates. 
        Use if q is already computed separately."""
    if len(q.shape) == 1:
        #no time axis
        delta_var = var_q[1]-var_q[0]
        out_Q = np.cumsum(q[::-1])[::-1]*delta_var
        out_Q = np.append(out_Q, np.zeros(1,), axis=0)
        var_Q = np.append(var_q-0.5*delta_var,
                          var_q[-1] + 0.5*delta_var)

        out = xr.Dataset({
        "Q": (["var_Q"], out_Q)},
        coords={
            "var_Q": (["var_Q"], var_Q),
        })

        return out
    
    elif len(q.shape) == 2 and var_q2 is None:
        #time axis existing, 1D TEF
        delta_var = var_q[1]-var_q[0]
        T = q.shape[0]
        out_Q = np.cumsum(q[:,::-1], axis=1)[:,::-1]*delta_var
        out_Q = np.append(out_Q,np.zeros((T,1)),axis=1)
        var_Q = np.append(var_q-0.5*delta_var,var_q[-1]+0.5*delta_var)
        
        out = xr.Dataset({
        "Q": (["time", "var_Q"], out_Q)},
        coords={
            "time": (["time"], _get_time_array(q)),
            "var_Q": (["var_Q"], var_Q),
        })

        return out

    elif len(q.shape) == 2 and var_q2 is not None:
        #no time axis existing, 2D TEF
        N_1 = q.shape[1]
        N_2 = q.shape[1]
        delta_var = var_q[1]-var_q[0]
        delta_var2 = var_q2[1]-var_q2[0]
        out_Q = np.zeros((N_1+1, N_2+1))
        out_Q_tmp = np.cumsum(np.cumsum(q[::-1,::-1],axis=0),axis=1)[::-1,::-1]*delta_var2*delta_var
        out_Q[:-1,:-1] = out_Q_tmp
        var_Q = np.append(var_q-0.5*delta_var,var_q[-1]+0.5*delta_var)
        var_Q2 = np.append(var_q2-0.5*delta_var2,var_q2[-1]+0.5*delta_var2)
        out = xr.Dataset({
        "Q2": (["var_Q", "var_Q2"], out_Q)},
        coords={
            "var_Q": (["var_Q"], var_Q),
            "var_Q2": (["var_Q2"], var_Q),
        })

        return out 

    elif len(q.shape) == 3 and var_q2 is not None:
        #time axis and 2D TEF
        T = q.shape[0]
        N_1 = q.shape[1]
        N_2 = q.shape[1]
        delta_var = var_q[1]-var_q[0]
        delta_var2 = var_q2[1]-var_q2[0]
        out_Q = np.zeros((T, N_1+1, N_2+1))
        out_Q_tmp = np.cumsum(np.cumsum(q[:,::-1,::-1],
                                        axis=1),
                                        axis=2)[:,::-1,::-1]*delta_var2*delta_var
        out_Q[:, :-1, :-1] = out_Q_tmp
        var_Q = np.append(var_q-0.5*delta_var,
                          var_q[-1]+0.5*delta_var)
        var_Q2 = np.append(var_q2-0.5*delta_var2,
                           var_q2[-1]+0.5*delta_var2)

        out = xr.Dataset({
        "Q2": (["time", "var_Q", "var_Q2"], out_Q)},
        coords={
            "time": (["time"], _get_time_array(q)),
            "var_Q": (["var_Q"], var_Q),
            "var_Q2": (["var_Q2"], var_Q),
        })

        return out     

# %% ../01_calc.ipynb 6
def sort_1dim(constructorTEF,
              N = 1024,
              minmaxrange = None):
    """Performs coordinate transformation by given variable."""
    if constructorTEF.tracer is None:
        raise ValueError("Please define a variable that you want to sort by.")
    if constructorTEF.transport is None:
        raise ValueError("Please provide transport term.")

    if minmaxrange is None:
        varmin = np.floor(constructorTEF.tracer.min().values)
        varmax = np.ceil(constructorTEF.tracer.max().values)
    else:
        if minmaxrange[0] > constructorTEF.tracer.min().values:
            print("Warning: Given minimum value is greater than the minimum value of the variable.")
            print("Warning: Given {}, minmum value of variable {}".format(minmaxrange[0],
                                                                 constructorTEF.tracer.min().values))
        if minmaxrange[-1] < constructorTEF.tracer.max().values:
            print("Warning: Given maximum value is smaller than the maximum value of the variable.")
            print("Warning: Given {}, maximum value of variable {}".format(minmaxrange[-1],
                                                                 constructorTEF.tracer.max().values))
        if type(minmaxrange) != "numpy.ndarray" and type(minmaxrange) is not tuple:
            raise ValueError("Please provide array range, e.g. np.arange(0,10), or a tuple, e.g. (0,10).")

        else:
            varmin = minmaxrange[0]
            varmax = minmaxrange[-1]

    if type(minmaxrange) == "numpy.ndarray":
        print('Using provided numpy array')

        var_q = minmaxrange.copy()

        #check if equidistant
        if np.unique(np.diff(var_q)) != 1:
            print('Warning: Provided array is not equidistant, but the function assumes equidistance!')
        delta_var = var_q[1]-var_q[0]

        var_Q = np.arange(var_q-0.5*delta_var,
                          var_q[-1]+0.5*delta_var,
                          delta_var)
    else:
        print('Constructing var_q and var_Q')
        delta_var = ((varmax-varmin)/N)

        var_q = np.linspace(varmin + 0.5*delta_var,
                            varmax - 0.5*delta_var,
                            N)
        var_Q = np.linspace(varmin, varmax, N+1)

    # Changelog: 27.05.2021: Change var_Q to var_q
    # compute the index idx that will be used for sorting
    idx = xr.apply_ufunc(np.digitize, constructorTEF.tracer, var_q) 

    out_q = np.zeros((len(constructorTEF.ds.time), N))

    for i in tqdm(range(N)):
        #Sorting into bins
        out_q[:, i] = constructorTEF.transport.where(idx == i).sum(["depth",
                                                                    "lat",
                                                                    "lon"],
                                                     dtype=np.float64) / delta_var
    
    out_Q = np.append(np.cumsum(out_q[:,::-1],
                                axis=1)[:,::-1],
                      np.zeros((len(constructorTEF.ds.time), 1)),axis=1)*delta_var
    
    out = xr.Dataset({
    "q": (["time", "var_q"], out_q),
    "Q": (["time", "var_Q"], out_Q)},
    coords={
        "time": (["time"], constructorTEF.ds["time"].data),
        "var_q": (["var_q"],var_q),
        "var_Q": (["var_Q"], var_Q),
    })
    
    return out

# %% ../01_calc.ipynb 9
def sort_2dim(constructorTEF,      
              N = (1024, 1024),
              minmaxrange = None,
              minmaxrange2 = None):
        """Sort transport by two given variables"""
        if constructorTEF.tracer[0] is None:
            raise ValueError("Please define a variable that you want to sort by.")
        if constructorTEF.tracer[1] is None:
            raise ValueError("Please define a second variable that you want to sort by.")    

        if constructorTEF.transport is None:
            raise ValueError("Please provided transport term.")

        if minmaxrange is None:
            varmin = np.floor(constructorTEF.tracer[0].min().values)
            varmax = np.ceil(constructorTEF.tracer[0].max().values)      
        else:
            if minmaxrange[0] > constructorTEF.tracer[0].min().values:
                print("Warning: Given minimum value is gretaer than the minimum value of the variable.")
                print("Warning: Given {}, minmum value of variable {}".format(minmaxrange[0],
                                                                     constructorTEF.tracer[0].min().values))
            if minmaxrange[-1] < constructorTEF.tracer[0].max().values:
                print("Warning: Given maximum value is smaller than the maximum value of the variable.")
                print("Warning: Given {}, maximum value of variable {}".format(minmaxrange[-1],
                                                                     constructorTEF.tracer[0].max().values))
            if type(minmaxrange) != "numpy.ndarray" and type(minmaxrange) is not tuple:
                raise ValueError("Please provide array range, e.g. np.arange(0,10), or a tuple, e.g. (0,10).")
            else: 
                print("minmaxrange is a tuple")
                varmin = minmaxrange[0]
                varmax = minmaxrange[-1]

        if minmaxrange2 is None:
            varmin2 = np.floor(constructorTEF.tracer[1].min().values)
            varmax2 = np.ceil(constructorTEF.tracer[1].max().values)
        else:
            if minmaxrange2[0] > constructorTEF.tracer[1].min().values:
                print("Warning: Given minimum value is greater than the minimum value of the variable.")
                print("Warning: Given {}, minmum value of variable {}".format(minmaxrange2[0],
                                                                     constructorTEF.tracer[1].min().values))
            if minmaxrange2[-1] < constructorTEF.tracer[1].max().values:
                print("Warning: Given maximum value is smaller than the maximum value of the variable.")
                print("Warning: Given {}, maximum value of variable {}".format(minmaxrange2[-1],
                                                                     constructorTEF.tracer[1].max().values))
            if type(minmaxrange2) != "numpy.ndarray" and type(minmaxrange2) is not tuple:
                raise ValueError("Please provide array range, e.g. np.arange(0,10), or a tuple, e.g. (0,10).")
            else:    
                print("minmaxrange2 is a tuple")
                varmin2 = minmaxrange2[0]
                varmax2 = minmaxrange2[-1]
     
        if type(N) is tuple:
            N1 = N[0]
            N2 = N[1]

        if type(minmaxrange) == "numpy.ndarray":
            print('Using provided numpy array for variable 1')

            var_q = minmaxrange

            #check if equidistant
            diff=np.diff(np.diff(var_q))
            if len(diff[diff!=0]) != 0:
                print('Warning: Provided array for variable1 is not equidistant, but the function assumes equidistance!')
            delta_var=var_q[1]-var_q[0]

            var_Q = np.arange(var_q-0.5*delta_var, var_q[-1]+0.5*delta_var, delta_var)
        else:
            #constructing
            delta_var = ((varmax-varmin)/N1)           
            var_q = np.linspace(varmin + 0.5*delta_var,
                                varmax - 0.5*delta_var,
                                N1)                           
            var_Q = np.linspace(varmin, varmax, N1+1)

        if type(minmaxrange2) == "numpy.ndarray":
            print('Using provided numpy array for variable 2')

            var_q2 = minmaxrange2

            #check if equidistant
            diff=np.diff(np.diff(var_q2))
            if len(diff[diff!=0]) != 0:
                print('Warning: Provided array for variable2 is not equidistant, but the function assumes equidistance!')
            delta_var2=var_q2[1]-var_q2[0]

            var_Q2 = np.arange(var_q2-0.5*delta_var2, var_q2[-1]+0.5*delta_var2, delta_var2)
        else:
            #contructing
            delta_var2 = ((varmax2-varmin2)/N2)
            var_q2 = np.linspace(varmin2 + 0.5*delta_var2,
                                 varmax2 - 0.5*delta_var2,
                                 N2)
            var_Q2 = np.linspace(varmin2, varmax2, N2+1)

        #sortingt
        idx = xr.apply_ufunc(np.digitize, constructorTEF.tracer[0], var_Q)
        idy = xr.apply_ufunc(np.digitize, constructorTEF.tracer[1], var_Q2)

        out_q = np.zeros((len(constructorTEF.ds.time),N1, N2))
        
        for i in tqdm(range(N1)):
            for j in range(N2):
                indices = (idx == i) & (idy == j)
                if indices.any():
                    out_q[:, i, j] = constructorTEF.transport.where(indices).sum(["depth", "lat", "lon"],
                                                                                 dtype=np.float64) / delta_var / delta_var2
                else:
                    out_q[:, i, j] = np.NaN
        
        out_Q = np.zeros((len(constructorTEF.ds.time), N1+1, N2+1))
        out_Q_tmp = np.cumsum(np.cumsum(out_q[:,::-1,::-1],axis=1),axis=2)[:,::-1,::-1]*delta_var2*delta_var
        out_Q[:,:-1,:-1] = out_Q_tmp
        
        out = xr.Dataset({
        "q2": (["time", "var_q", "var_q2"], out_q),
        "Q2": (["time", "var_Q", "var_Q2"], out_Q)},
        coords={
            "time": (["time"], constructorTEF.ds["time"].data),
            "var_q": (["var_q"],var_q),
            "var_q2": (["var_q2"], var_q2),
            "var_Q": (["var_Q"], var_Q),
            "var_Q2": (["var_Q2"], var_Q2),
        })
        
        return out

# %% ../01_calc.ipynb 12
def calc_bulk_values(coord,
                     Q,
                     Qc=None,
                     Q_thresh=None,
                     index=None,
                     ):
    """Calculate the bulk values from a provided Q profile.

    This methods uses the dividing salinity approach proposed by MacCready
    et al. (2018) and described/tested in detail by Lorenz et al. (2019).

    If a tracer transport Qc is provided, also its bulk values are computed.
    """
    coord_min=coord[0]
    delta_var=coord[1]-coord[0]

    if len(Q.shape) > 1:
        
        #first dimension is time! -> keep this dimension!
        #prepare storage arrays for Qin, Qout, consider multiple inflow/outflows! 

        Qin_ar = np.zeros((Q.shape[0],10)) #10 is the dummy length
        Qout_ar = np.zeros((Q.shape[0],10))
        if Qc is not None:
            Qc_in_ar = np.zeros((Q.shape[0], 10))
            Qc_out_ar = np.zeros((Q.shape[0], 10))
        divval_ar = np.zeros((Q.shape[0],11)) #if there are 10 transports there would be 11 dividing salinities
        indices = np.zeros((Q.shape[0],11))

        for t in tqdm(np.arange(Q.shape[0])):
            if Q_thresh is None:
                #set a default thresh
                Q_thresh=0.01*np.max(np.abs(Q[t]))
            if index is None:
                ind,minmax = _find_extrema(Q[t],Q_thresh)
            else:
                ind=np.copy(index[t])
                ind=ind[ind!=0]

            div_val=[]
            i=0
            for i in range(len(ind)):
                div_val.append(coord_min+delta_var*ind[i])
                i+=1
                #calculate transports etc.
            Q_in_m=[]
            Q_out_m=[]
            if Qc is not None:
                Qc_in = []
                Qc_out = []
            index_del=[]
            i=0
            for i in range(len(ind)-1):
                Q_i=-(Q[t,ind[i+1]]-Q[t,ind[i]])
                if Qc is not None:
                    Qc_i = -(Qc[t, ind[i+1]] - Qc[t, ind[i]])
                if Q_i<0:
                    Q_out_m.append(Q_i)
                    if Qc is not None:
                        Qc_out.append(Qc_i)
                elif Q_i > 0:
                    Q_in_m.append(Q_i)
                    if Qc is not None:
                        Qc_in.append(Qc_i)
                else:
                    index_del.append(i)
                i+=1
            div_val = np.delete(div_val, index_del)
            ind = np.delete(ind, index_del)

            #storing results
            for i,qq in enumerate(Q_in_m):
                Qin_ar[t,i] = qq
            for i,qq in enumerate(Q_out_m):
                Qout_ar[t,i] = qq
            if Qc is not None:
                for i,qq in enumerate(Qc_in):
                    Qc_in_ar[t,i] = qq
                for i,qq in enumerate(Qc_out):
                    Qc_out_ar[t,i] = qq
            for i,ss in enumerate(div_val):
                divval_ar[t,i] = ss
            for i,ss in enumerate(ind):
                indices[t,i] = ss

        #create a xarray Dataset for the results
        out = xr.Dataset(
        {
            "Qin": (["time", "m"], np.array(Qin_ar)),
            "Qout": (["time", "n"], np.array(Qout_ar)),
            "divval": (["time", "o"], np.array(divval_ar)),
            "index": (["time","o"], np.array(indices).astype(int)),
        },
        coords={
            "time": (["time"], Q.time.data),
            "m": (["m"],np.arange(Qin_ar.shape[1])),
            "n": (["n"],np.arange(Qout_ar.shape[1])),
            "o": (["o"],np.arange(divval_ar.shape[1])),
        },
        )
        if Qc is not None:
            out["Qc_in"] = (["time", "m"], Qc_in_ar)
            out["Qc_out"] = (["time", "n"], Qc_out_ar)

    else:
        #no time axis
        if Q_thresh is None:
        #set a default thresh
            Q_thresh=0.01*np.max(np.abs(Q))
        
        if index is None:
            ind,minmax = _find_extrema(Q,Q_thresh)
        else:
            ind=np.copy(index)
        div_val=[]
        i=0
        while i < len(ind):
                #print(Qvl[ind[i]])
            div_val.append(coord_min+delta_var*ind[i])
            i+=1
                #print(smin+dss*ind[i])
            #calculate transports etc.
        Q_in_m=[]
        Q_out_m=[]
        if Qc is not None:
            Qc_in = []
            Qc_out = []
        index_del=[]
        i=0
        for i in tqdm(range(len(ind)-1)):
            Q_i=-(Q[ind[i+1]]-Q[ind[i]])
            if Qc is not None:
                Qc_i = -(Qc[ind[i+1]] - Qc[ind[i]])
            if Q_i<0:
                Q_out_m.append(Q_i)
                if Qc is not None:
                    Qc_out.append(Qc_i)
            elif Q_i > 0:
                Q_in_m.append(Q_i)
                if Qc is not None:
                    Qc_in.append(Qc_i)
            else:
                index_del.append(i)
            i+=1
        div_val = np.delete(div_val, index_del)
        ind = np.delete(ind, index_del)

        out = xr.Dataset(
        {
            "Qin": (["m"], np.array(Q_in_m)),
            "Qout": (["n"], np.array(Q_out_m)),
            "divval": (["o"], np.array(div_val)),
            "index": (["o"], np.array(ind)),
        },
        coords={
            "m": (["m"],np.arange(len(Q_in_m))),
            "n": (["n"],np.arange(len(Q_out_m))),
            "o": (["o"],np.arange(len(div_val))),
        }
        )
        if Qc is not None:
            out["Qc_in"] = (["m"], Qc_in)
            out["Qc_out"] = (["n"], Qc_out)
    return(out)

# %% ../01_calc.ipynb 15
def _get_time_array(x):
    #check if x has a time property, i.e. is a dataset
    if isinstance(x, np.ndarray):
        print('numpy array -> creating artificial time axis')
        time_array=np.arange(x.shape[0])
    elif isinstance(x,xr.Dataset) or isinstance(x,xr.DataArray):
        print('is xr.Dataset or xr.DataArray')
        if not 'time' in x.dims:
            print('has no time axis -> creating artificial one')
            time_array=np.arange(x.shape[0])
        else:
            print('using existing time axis')
            time_array = x['time']
    else:
        #create an artificial time array
        time_array=np.arange(x.shape[0])
    return time_array

# %% ../01_calc.ipynb 16
def _find_extrema(x, min_transport):
    """
    internal function called by calc_bulk values to find the extrema in the transport function x
    and label them correctly, see Appendix B in Lorenz et al. (2019).
    x: Q(S)
    min_transport: Q_thresh
    """
    if np.count_nonzero(x)==0 or np.isnan(x).all():
        indices=[0]
        minmax=[0]
        return(indices,minmax)
    else:
        ###
        #set a minimum value to get rid of numerical noise
        ###
        if min_transport<=10**(-10):
            min_transport=10**(-10)

        ####
        #finding all extrema by evaluating each data point
        ####
        comp=1
        indices = []
        minmax = []
        i = 0
        while i < np.shape(x)[0]:
            if i-comp < 0:
                a = 0
            else:
                a=i-comp
            if i+comp+1>=len(x):
                b=None
                #c=i
            else:
                b=i+comp+1
                #c=b
            if x[i] == np.max(x[a:b]) and np.max(x[a:b]) != np.min(x[a:b]):# and x[i] != x[a]:
                indices.append(i)
                minmax.append('max')
            elif x[i] == np.min(x[a:b]) and np.max(x[a:b]) != np.min(x[a:b]):# and (x[i] != x[c] or x[i] != x[a]):
                indices.append(i)
                minmax.append('min')
            i+=1
        #print(indices,minmax)
        #print(x[indices])

        ###
        #correct consecutive extrema of the same kind, e.g., min min min or max max max (especially in the beginning and end of the salinity array)
        ###

        #index=[]
        ii=1
        while ii < len(indices):
            index=[]
            if minmax[ii] == minmax[ii-1]:
                if minmax[ii] == 'max': #note the index of the smaller maximum
                    if x[indices[ii]]>=x[indices[ii-1]]:
                        index.append(ii-1)
                    else:
                        index.append(ii)
                elif minmax[ii] == 'min': #note the index of the greater minimum
                    if x[indices[ii]]<=x[indices[ii-1]]:
                        index.append(ii-1)
                    else:
                        index.append(ii)
                minmax = np.asarray(minmax)
                indices = np.asarray(indices)
                indices = np.delete(indices, index)
                minmax = np.delete(minmax, index)
            else:
                ii+=1

        ####
        #delete too small transports
        ####

        ii=0
        while ii < len(indices)-1: 
            index=[]
            if np.abs(x[indices[ii+1]]-x[indices[ii]]) < min_transport:
                if ii == 0: #if smin is involved and the transport is too small, smin has to change its min or max property
                    index.append(ii+1)
                    if minmax[ii] == 'min':
                        minmax[ii] = 'max'
                    else:
                        minmax[ii] = 'min'
                elif ii+1==len(indices)-1:#if smax is involved and the transport is too small, smin has to change its min or max property
                    index.append(ii)
                    if minmax[ii+1] == 'min':
                        minmax[ii+1] = 'max'
                    else:
                        minmax[ii+1] = 'min'
                else: #else both involved div sals are kicked out
                    if ii+2 < len(indices)-1:
                    #check and compare to i+2
                        if minmax[ii]=='min':
                            if x[indices[ii+2]]>x[indices[ii]]:
                                index.append(ii+2)
                                index.append(ii+1)
                            else:
                                index.append(ii)
                                index.append(ii+1)
                        elif minmax[ii]=='max':
                            if x[indices[ii+2]]<x[indices[ii]]:
                                index.append(ii+2)
                                index.append(ii+1)
                            else:
                                index.append(ii)
                                index.append(ii+1)
                    else:
                        index.append(ii)
                        index.append(ii+1)
                indices = np.delete(indices, index)
                minmax = np.delete(minmax, index)
            else:
                ii+=1

        ###
        #so far the first and last minmax does not correspond to smin and smax of the data, expecially smin due to numerical errors (only makes sense)
        #correct smin index
        ###

        if len(x)>4:
            ii=1
            while np.abs(np.abs(x[ii])-np.abs(x[0])) < 10**(-10) and ii < len(x)-1:
                ii+=1
            indices[0]=ii-1
            #correct smax index
            if x[-1]==0: #for low salinity classes Q[-1] might not be zero as supposed.
                jj=-1
                while x[jj] == 0 and np.abs(jj) < len(x)-1:
                    jj -=1
                indices[-1] = len(x)+jj+1
        return indices,minmax
