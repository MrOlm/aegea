"""
Manage AWS EC2 Elastic Load Balancers (ELBs).
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os, sys, argparse

from . import register_parser
from .util import Timestamp, paginate
from .util.printing import format_table, page_output, get_field, get_cell, tabulate
from .util.aws import ARN, resources, clients, resolve_instance_id, get_elb_dns_aliases

def elb(args):
    elb_parser.print_help()

elb_parser = register_parser(elb, help='Manage Elastic Load Balancers', description=__doc__,
                             formatter_class=argparse.RawTextHelpFormatter)

def ls(args):
    table = []
    dns_aliases = get_elb_dns_aliases()
    for row in paginate(clients.elb.get_paginator('describe_load_balancers')):
        row["alias"] = dns_aliases.get(row["DNSName"])
        instances = clients.elb.describe_instance_health(LoadBalancerName=row["LoadBalancerName"])["InstanceStates"]
        table.extend([dict(row, **instance) for instance in instances] if instances else [row])
    page_output(tabulate(table, args))

parser = register_parser(ls, parent=elb_parser)

def register(args):
    instances = [dict(InstanceId=i) for i in args.instances]
    res = clients.elb.register_instances_with_load_balancer(LoadBalancerName=args.elb_name, Instances=instances)
    return dict(registered=args.instances, current=[i["InstanceId"] for i in res["Instances"]])

parser = register_parser(register, parent=elb_parser, help="Add EC2 instances to an ELB")
parser.add_argument("elb_name")
parser.add_argument("instances", nargs="+", type=resolve_instance_id)

def deregister(args):
    instances = [dict(InstanceId=i) for i in args.instances]
    res = clients.elb.deregister_instances_from_load_balancer(LoadBalancerName=args.elb_name, Instances=instances)
    return dict(deregistered=args.instances, current=[i["InstanceId"] for i in res["Instances"]])

parser = register_parser(deregister, parent=elb_parser, help="Remove EC2 instances from an ELB")
parser.add_argument("elb_name")
parser.add_argument("instances", nargs="+", type=resolve_instance_id)

def replace(args):
    result = register(args)
    old_instances = set(result["current"]) - set(result["registered"])
    if old_instances:
        args.instances = list(old_instances)
        result.update(deregister(args))
    return result

parser = register_parser(replace, parent=elb_parser, help="Replace all EC2 instances in an ELB with the ones given")
parser.add_argument("elb_name")
parser.add_argument("instances", nargs="+", type=resolve_instance_id)
