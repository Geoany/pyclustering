from nnet.sync import *;

from support import draw_clusters;
from support import read_sample;

class syncnet(net):
    _loc = None;
    
    def __init__(self, source_data, conn_repr = conn_represent.MATRIX):
        sample = None;
        if ( isinstance(source_data, str) ):
            file = open(source_data, 'r');
            sample = [[float(val) for val in line.split()] for line in file];
            file.close();
        else:
            sample = source_data;
        
        super().__init__(len(sample), 1, False, conn_type.NONE);
        
        self._osc_loc = sample;
        self._conn_represent = conn_repr;

        # Connections will be represent by lists.
        if (conn_repr == conn_represent.MATRIX):
            self._osc_conn = [[0] * self._num_osc for index in range(0, self._num_osc, 1)];
            
        elif (conn_repr == conn_represent.LIST):
            self._osc_conn = [[] for index in range(0, self._num_osc, 1)];
            
        else:
            raise NameError("Unknown type of representation of coupling between oscillators");
        
        

    def __create_connections(self, radius):
        "Create connections between oscillators"
        # Create connections
        for i in range(0, self._num_osc, 1):
            for j in range(0, self._num_osc, 1):
                dist = euclidean_distance(self._osc_loc[i], self._osc_loc[j]);
                if (dist <= radius):
                    if (self._conn_represent == conn_represent.LIST):
                        self._osc_conn[i].append(j);
                    else:
                        self._osc_conn[i][j] = True;
        
        
    def set_connections(self, osc_conn):
        if  ( (len(osc_conn) == len(self._osc_conn)) and (len(osc_conn[0]) == len(self._osc_conn[0])) ):
            self._osc_conn = osc_conn;
            
            

    def process(self, radius = None, order = 0.998, solution = solve_type.FAST, collect_dynamic = False):
        "Network is trained via achievement sync state between the oscillators using the radius of coupling"
        # Create connections in line with input radius
        if (radius != None):
            self.__create_connections(radius);
        
        # For statistics
        iter_counter = 0;
        
        # If requested input dynamics
        dyn_phase = None;
        dyn_time = None;
        if (collect_dynamic == True):
            dyn_phase = list();
            dyn_time = list();
            
            dyn_phase.append(self._phases);
            dyn_time.append(0);
        
        # Execute until sync state will be reached
        while (self.sync_local_order() < order):
            iter_counter += 1;
            next_phases = [0] * self.num_osc;    # new oscillator _phases
            
            for index in range (0, self.num_osc, 1):
                if (solution == solve_type.FAST):
                    result = self._phases[index] + self.phase_kuramoto(self._phases[index], 0, index);
                    next_phases[index] = phase_normalization(result);
                    
                elif (solution == solve_type.ODEINT):
                    result = odeint(self.phase_kuramoto, self._phases[index], numpy.arange(0, 0.1, 1), (index , ));
                    next_phases[index] = phase_normalization(result[len(result) - 1][0]);
                    
                else:
                    assert 0;   # Should be implemented later.
                    
            # update states of oscillators
            self._phases = next_phases;
            
            # If requested input dynamic
            if (collect_dynamic == True):
                dyn_phase.append(next_phases);
                dyn_time.append(iter_counter);
        
        print("Number of iteration: ", iter_counter);
        return (dyn_time, dyn_phase);
    
    
    def get_neighbors(self, index):
        "Return list of neighbors of a oscillator with sequence number 'index'"
        if (self._conn_represent == conn_represent.LIST):
            return self._osc_conn[index];      # connections are represented by list.
        elif (self._conn_represent == conn_represent.MATRIX):
            return [neigh_index for neigh_index in range(self._num_osc) if self._osc_conn[index][neigh_index] == True];
        else:
            raise NameError("Unknown type of representation of connections");
    
    
    def phase_kuramoto(self, teta, t, argv):
        "Overrided method for calculation of oscillator phase"
        index = argv;   # index of oscillator
        phase = 0;      # phase of a specified oscillator that will calculated in line with current env. states.
        
        neighbors = self.get_neighbors(index);
        for k in neighbors:
            phase += math.sin(self._cluster * (self._phases[k] - teta));
            
        return ( self._freq[index] + (phase * self._weight / len(neighbors)) );   


    def get_clusters(self, eps = 0.1):
        clusters = [ [0] ];
        
        for i in range(1, self._num_osc, 1):
            cluster_allocated = False;
            for cluster in clusters:
                for neuron_index in cluster:
                    if ( (self._phases[i] < (self._phases[neuron_index] + eps)) and (self._phases[i] > (self._phases[neuron_index] - eps)) ):
                        cluster_allocated = True;
                        cluster.append(i);
                        break;
                
                if (cluster_allocated == True):
                    break;
            
            if (cluster_allocated == False):
                clusters.append([i]);
        
        #debug assert
        total_length = 0;
        for cluster in clusters:
            total_length += len(cluster);
        print("Total length: ", total_length, ", Real: ", self._num_osc);
        assert total_length == self._num_osc;
        
        return clusters;
    
    
    def show_network(self):
        "Show connections in the network. It supports only 2-d and 3-d representation."
        dimension = len(self._osc_loc[0]);
        if ( (dimension != 3) and (dimension != 2) ):
            raise NameError('Network that is located in different from 2-d and 3-d dimensions can not be represented');
        
        from matplotlib.font_manager import FontProperties;
        from matplotlib import rcParams;
    
        rcParams['font.sans-serif'] = ['Arial'];
        rcParams['font.size'] = 12;

        fig = plt.figure();
        axes = None;
        if (dimension == 2):
            axes = fig.add_subplot(111);
        elif (dimension == 3):
            axes = fig.gca(projection='3d');
        
        surface_font = FontProperties();
        surface_font.set_name('Arial');
        surface_font.set_size('12');
        
        for i in range(0, self.num_osc, 1):
            if (dimension == 2):
                axes.plot(self._osc_loc[i][0], self._osc_loc[i][1], 'bo');  
                if (self._conn_represent == conn_represent.MATRIX):
                    for j in range(i, self._num_osc, 1):    # draw connection between two points only one time
                        if (self.has_connection(i, j) == True):
                            axes.plot([self._osc_loc[i][0], self._osc_loc[j][0]], [self._osc_loc[i][1], self._osc_loc[j][1]], 'b-', linewidth=0.5);    
                            
                else:
                    for j in self.get_neighbors(i):
                        if ( (self.has_connection(i, j) == True) and (i > j) ):     # draw connection between two points only one time
                            axes.plot([self._osc_loc[i][0], self._osc_loc[j][0]], [self._osc_loc[i][1], self._osc_loc[j][1]], 'b-', linewidth=0.5);    
            
            elif (dimension == 3):
                axes.scatter(self._osc_loc[i][0], self._osc_loc[i][1], self._osc_loc[i][2], c = 'b', marker = 'o');
                # TODO: SOMETHING WRONG WITH CONNECTIONS BUILDER. TOO LONG AND AREN'T DISPLAYED 
                #if (self._conn_represent == conn_represent.MATRIX):
                #    for j in range(i, self._num_osc, 1):    # draw connection between two points only one time
                #        axes.scatter([self._osc_loc[i][0], self._osc_loc[j][0]], [self._osc_loc[i][1], self._osc_loc[j][1]], [self._osc_loc[i][2], self._osc_loc[j][2]], c = 'b');
                #        
                #else:
                #    for j in self.get_neighbors(i):
                #        if ( (self.has_connection(i, j) == True) and (i > j) ):     # draw connection between two points only one time
                #            axes.scatter([self._osc_loc[i][0], self._osc_loc[j][0]], [self._osc_loc[i][1], self._osc_loc[j][1]], [self._osc_loc[i][2], self._osc_loc[j][2]], c = 'b');
                               
        plt.grid();
        plt.show();
    


# sample = read_sample('../Samples/SampleLsun.txt');
# network = syncnet(sample);
# (dyn_time, dyn_phase) = network.process(0.5, 0.995, collect_dynamic = True);
# 
# draw_dynamics(dyn_time, dyn_phase);
# 
# clusters = network.get_clusters(0.05);
# draw_clusters(sample, clusters);