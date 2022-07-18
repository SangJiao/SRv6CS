# -*- coding: utf-8 -*-
import json
from multiprocessing import Pool, cpu_count

import z3
import networkx as nx
import os

from utils.keyword import *


def get_simple_paths(parts):
    """
    path同起点同终点的所有简单路径
    :param : set[0] mode: order+拓扑图+路径
    :return: (path, others_paths)
    """
    mode = parts[0]  # equal cost multi paths or order path
    path_list = parts[1]  # paths of policy
    req_graph = parts[2]

    assert len(path_list) >= 1  # 表达式为真，正常执行
    src = path_list[0].nodes_list[0]
    dst = path_list[0].nodes_list[-1]
    other_paths = list(nx.shortest_simple_paths(req_graph, source=src, target=dst))  # 可行路径
    new_path_list = []
    for path in path_list:
        new_path_list.append(path.nodes_list)
        other_paths.remove(path.nodes_list)
    return (mode, new_path_list, other_paths)


# 输入文件 ----网络拓扑等 inputs
# 输出文件  -----需求文件 fixed——out
class ISIS_Synthesizer(object):
    def __init__(self, topo, isis_policy, log_signal=None, process=MULT, out_dir=""):
        assert (isinstance(topo, nx.DiGraph))
        self.topology = topo
        self.isis_policy = isis_policy
        self.process = process
        self.log_signal = log_signal
        self.out_dir = out_dir

        self.node_names = []
        self.interface_names = []
        self.edge_node_to_inter = {}

        self.req_paths_sat = []  # 记录路径需求
        self.all_req_paths = []
        self.req_edges = []  # 需求涵盖的边
        self.req_graph = nx.DiGraph()  # 根据需求生成的拓扑

        self.edges_to_cost_z3 = {}  # 边和 cost_z3 的一一对应
        self.isis_costs={}
        self.cost_z3 = []  # cost值
        self.constraints = []  # 生成的约束

        self.get_necessary_info()

        self.create_z3_value()

        self.get_values_constraints()

        self.get_reqs_constraints()

    def output(self, text):
        if self.log_signal is None:
            print(text)
        else:
            t = str(text)
            self.log_signal.emit(t)

    """
    """
    def get_necessary_info(self):
        self.node_names = [node[0] for node in self.topology.nodes(data=True) if node[1][TYPE] == NODE]
        # nodes:['A', 'A_int_1', 'A_int_2', 'B', 'B_int_1', 'B_int_2'......]
        # nodes_names:['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        # (data=True表示返回NodeDataView，顶点后面是字典，表示节点的属性)
        self.interface_names = [node[0] for node in self.topology.nodes(data=True) if node[1][TYPE] == INTERFACE]
        for edge in self.topology.edges(data=True):
            data = edge[2]
            if data[TYPE] == LINK_EDGE:
                src_inter = edge[0]
                dst_inter = edge[1]
                src_node = [node for node in self.topology.neighbors(src_inter) if node != dst_inter][0]
                dst_node = [node for node in self.topology.neighbors(dst_inter) if node != src_inter][0]
                self.edge_node_to_inter[(src_node, dst_node)] = (src_inter, dst_inter)
        edges = []
        for mode, path_list, exc, name in self.isis_policy:
            for path in path_list:
                assert (path.op == POS)
                for index, node in enumerate(path.nodes_list[:-1]):
                    edges.append((path.nodes_list[index], path.nodes_list[index + 1]))

        self.req_edges = list(set(edges))
        self.req_graph.add_edges_from(self.req_edges)

    def create_z3_value(self):
        """
        创建对应的z3变量
        :return:
        """
        for edge in self.req_edges:  # 定义cost值的z3表达
            cost = z3.Int('%s_%s_cost' % (edge[0], edge[1]))
            self.cost_z3.append(cost)
            self.edges_to_cost_z3[(edge[0], edge[1])] = cost
        # print self.edges_to_cost

    def get_values_constraints(self):
        """
        生成cost取值范围约束
        :return: None
        """
        vals_cons = [z3.And(cost > 0, cost < MAX_OSPF_COST) for cost in self.cost_z3]
        self.constraints.append(z3.And(vals_cons))

    def sum(self, path):
        """
        对path表示的路径求链路权值cost之和
        :param path: 待计算路径
        :return: None
        """
        sum = z3.Int('sum')
        sum = self.edges_to_cost_z3[(path[0], path[1])]
        for index, node in enumerate(path[0:-1]):
            if index > 0:
                sum += self.edges_to_cost_z3[(path[index], path[index + 1])]
        return sum

    def get_single_req_constraints(self, mode, path_list, other_paths):

        cons = []
        if mode == SIMPLE and len(other_paths) >= 1:

            for other_path in other_paths:
                cons.append(self.sum(path_list[0]) < self.sum(other_path))  # 不等式约束
        elif mode == ECMP:
            assert len(path_list) >= 2
            for path in path_list[1::]:
                cons.append(self.sum(path_list[0]) == self.sum(path))
            for other_path in other_paths:
                cons.append(self.sum(path_list[0]) < self.sum(other_path))
        elif mode == ORDER:
            assert len(path_list) >= 2
            for index, path in enumerate(path_list[:-1]):
                cons.append(self.sum(path) < self.sum(path_list[index + 1]))
            last_path = path_list[-1]
            for other_path in other_paths:
                cons.append(self.sum(last_path) < self.sum(other_path))
        return cons

    def get_reqs_constraints(self):
        """
        获得路径的不等式约束
        :return: None
        """
        cons = []
        if self.process == MULT:  # 多进程
            args = []
            for mode, path_list, exc, name in self.isis_policy:
                G = nx.DiGraph(self.req_graph)
                if exc:
                    exc_nodes = exc[0]
                    exc_edges = exc[1]
                    if exc_edges:
                        G.remove_edges_from(exc_edges)
                    if exc_nodes:
                        G.remove_nodes_from(exc_nodes)
                args.append((mode, path_list, G))

            pool = Pool(cpu_count())  # 创建cpu核心数目的进程
            reqs = pool.map(get_simple_paths, args)  # 向进程池添加任务
            pool.close()  # 关闭进程池
            pool.join()  # 阻塞
            for mode, path_list, other_paths in reqs:
                req_cons = self.get_single_req_constraints(mode, path_list, other_paths)
                cons += req_cons
        elif self.process == SINGLE:  # 单进程
            for mode, dst, path_list, name in self.isis_policy:

                src = path_list[0][0]
                other_paths = list(nx.shortest_simple_paths(self.req_graph, source=src, target=dst))  # 可行路径
                for path in path_list:
                    other_paths.remove(path)
                req_cons = self.get_single_req_constraints(mode, path_list, other_paths)

                cons += req_cons

        self.constraints.append(z3.And(cons))

    def synthesize(self):
        """
        z3求解器求解，判断约束合理性，获得可行解
        :return: None
        """
        # 添加取值约束
        self.output('Synthesizing ISIS  ....')
        self.solver = z3.Solver()
        self.solver.push()
        self.solver.append(self.constraints)
        if self.solver.check() == z3.sat:
            self.output("Sythesize ISIS succeed !!!")
            self.output('Output ISIS cost...')
            self.output('*' * 20)
            model = self.solver.model()
            cost_z3_to_edges = {v: k for k, v in self.edges_to_cost_z3.items()}
            cost_list = []
            for cost in self.cost_z3:
                src = cost_z3_to_edges[cost][0]
                dst = cost_z3_to_edges[cost][1]
                self.isis_costs[self.edge_node_to_inter[(src, dst)]] = model[cost].as_long()
                self.output('( ' + src + ' , ' + dst + ' , ' + str(model[cost].as_long()) + ' )')
                cost_list.append((src, self.edge_node_to_inter[(src, dst)][0], model[cost].as_long()))
            # self.output model
            self.output('*' * 20)

            with open(os.path.join(self.out_dir, "isis_costs.json"), 'w', encoding='utf-8') as f:
                f.write(json.dumps(cost_list, indent=4, default=lambda obj: obj.__dict__))
        else:
            self.output("Sythesize ISIS failed !!!")
            exit(-1)
        return self.isis_costs

    def is_path_req_sat(self, reqs, checked_mode, checked_path_list):
        """
        判断需求合理性
        :param reqs: 已经检查的需求集合
        :param checked_mode: 待检查需求类型
        :param checked_paths: 待检查需求路径
        :return:
        """
        assert len(checked_path_list) >= 1

        # for mode, dst_net, path_list in reqs:
        #     for checked_path in checked_path_list:
        #         for i, src in enumerate(checked_path):
        #             for j, dst in enumerate(checked_path):
        #                 if i >= j:
        #                     continue
        #                 for path in path_list:
        #                     if src in path and dst in path:
        #                         head = path.index(src)
        #                         tail = path.index(dst)
        #                         if head < tail:
        #                             list = path[head:tail+1]
        #                             if list != checked_path[i:j+1]:
        #                                 print('The following path requirments error !!')
        #                                 print((mode, dst_net, path_list))
        #                                 print((checked_mode, checked_path_list[0][-1], checked_path_list))
        #                                 exit(-1)

        return True

    # def verify_answer(self):
    #     """
    #     对z3求解出的结果进行验证
    #     :return:
    #     """
    #     G = nx.DiGraph()
    #     G.add_nodes_from(self.node_names)
    #     # 添加边
    #     edges = [(link[0], link[3]) for link in self.edge_node_to_inter]
    #     nodes_to_inter_link = {(link[0], link[3]):(link[1],link[2]) for link in self.edge_node_to_inter}
    #     G.add_edges_from(edges)
    #     for src, nbrs in G.adjacency_iter():
    #         for dst, attr in nbrs.items():
    #             inter_link = nodes_to_inter_link[(src, dst)]
    #             if inter_link in self.isis_costs.keys():
    #                 attr['weight'] = self.isis_costs[inter_link]
    #             else:
    #                 attr['weight'] = 65530

    #     for path in self.all_req_paths:
    #         assert len(path) >= 2
    #         path_actual = nx.shortest_path(G, source = path[0], target = path[-1], weight = 'weight')
    #         if path != path_actual:
    #             print ("Verify paths failed!!! ")
    #             print(path)
    #             print(path_actual)
    #             return
    #     print ("Verify paths succeed!!!")
