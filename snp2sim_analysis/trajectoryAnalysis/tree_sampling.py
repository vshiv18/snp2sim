import os
import sys
import argparse
import subprocess
import shutil
import yaml

class samplingTree():
	def __init__(self, parameters, run, scaff, parent):
		self.num = run
		self.scaff = scaff
		self.child = []
		self.parent = parent
		self.parameters = parameters
		if self.parent:
			self.depth = self.parent.depth + 1
		else:
			self.depth = 0
		if self.depth < self.parameters.depth:
			self.extend = True
		else:
			self.extend = False
	def addChild(self, node):
		self.child.append(node)
	def mark(self):
		self.extend = True

class argParse():
	def __init__(self):
		parser = argparse.ArgumentParser(
		#version="0.1",
		description="snp2sim - Molecular Simulation of Somatic Variation",
		epilog="written by Matthew McCoy, mdm299@georgetown.edu, and Vikram Shivakumar"
		)

		parser.add_argument("--config",
							help="use parameters from config.yaml. OVERWRITES command line parameters",
							action="store",
							)
		parser.add_argument("--depth",
							help="maximum depth to search for scaffolds",
							action="store",
							type=int,
							)
		parser.add_argument("--newStruct",
							help="initial structure",
							action="store",
							)
		parameters, unknownparams = parser.parse_known_args()

		if (parameters.config):
				self.__dict__.update(yaml.load(open(parameters.config)))
		else:
			print("No config file given.")
			sys.exit(1)

		self.__dict__.update(parameters.__dict__)

	def setDefaults(self):
		if "." in self.protein:
			self.protein.replace(".", "_")
		if isinstance(self.varAA,list) and isinstance(self.varResID,list):
			if len(self.varAA) == len(self.varResID):
				self.variant = [str(self.varResID[x]) + self.varAA[x] for x in range(len(self.varAA))]
				self.variant = "_".join(self.variant)
			else:
				print("number of ResIDs does not match number of variant AAs.")
				print("Using WT structure for simulation")
				self.variant = "wt"
		elif self.varResID and self.varAA:
			self.variant = str(self.varResID) + self.varAA
		else:
			print("varResID and varAA not specified")
			print("Using WT structure for simulation")
			self.variant = "wt"


def runInstance(parameters, node):
	trajDir = "%s/variantSimulations/%s/results/%s/trajectory" % (parameters.runDIR, parameters.protein, parameters.variant)
	scaffDir = "%s/variantSimulations/%s/results/%s/scaffold" % (parameters.runDIR, parameters.protein, parameters.variant)
	if node.num == 0 and os.path.isdir(trajDir):
		shutil.rmtree(trajDir)
	if node.num == 0 and os.path.isdir(scaffDir):
		shutil.rmtree(scaffDir)
	if os.path.isdir(trajDir):
		os.rename(trajDir, trajDir + "_" + str(node.num - 1))
	if os.path.isdir(scaffDir):
		os.rename(scaffDir, scaffDir + "_" + str(node.num - 1))
	if not os.path.isdir(trajDir + "_" + str(node.num)):
		trajCommand = "python snp2sim.py --config %s --mode varMDsim --newStruct %s --simID %d" %(parameters.config, node.scaff, node.num)
		try:
			run_out = subprocess.check_output(trajCommand, shell = True)
			for line in run_out.decode().split("\n"):
				print(line)
		except subprocess.CalledProcessError as e:
			print("Error in varMDsim run %d: " %parameters.num)
			for line in e.output.decode().split("\n"):
				print(line)
			sys.exit(1)
	else:
		os.rename(trajDir + "_" + str(node.num), trajDir)
	if not os.path.isdir(scaffDir + "_" + str(node.num)):
		scaffCommand = "python snp2sim.py --config %s --mode varScaffold --scaffID %d" %(parameters.config, node.num)
		try:
			run_out = subprocess.check_output(scaffCommand, shell = True)
			for line in run_out.decode().split("\n"):
				print(line)
		except subprocess.CalledProcessError as e:
			print("Error in varScaffold run %d: \n" %parameters.num)
			for line in e.output.decode().split("\n"):
				print(line)
			sys.exit(1)
	else:
		os.rename(scaffDir + "_" + str(node.num), scaffDir)
	os.rename(trajDir, trajDir + "_" + str(node.num))
	os.rename(scaffDir, scaffDir + "_" + str(node.num))

def checkStopCondition(parameters):
	#true if stop growing leaves
	if hasattr(parameters, "rmsdThresh"):
		oldthresh = parameters.rmsdThresh
	else:
		oldthresh = 0
	updateRMSDThresh(parameters)
	if parameters.rmsdThresh == oldthresh:
		return True
	else:
		return False
def updateRMSDThresh(parameters):
	scaffDir = "%s/variantSimulations/%s/results/%s/scaffold" % (parameters.runDIR, parameters.protein, parameters.variant)
	for x in range(parameters.num):
		curRun = scaffDir + "_" + str(x)
		for file in os.listdir(curRun):
			if file.endswith("scaffold.pdb"):
				scaffList.append(curRun + "/" + file)

	calcPairwiseRMSD(scaffList)
	with open(parameters.matrix, "r") as f:
		parameters.rmsd = [list(map(int, x.split(','))) for x in f.readlines()]
		parameters.rmsdThresh = max([max(x) for x in parameters.rmsd])

def calcPairwiseRMSD(parameters, pdbs):
	parameters.matrix = "%s/variantSimulations/%s/config/%s.%s.scaffpairwiseRMSD.csv" % (parameters.runDIR, parameters.protein, parameters.protein, parameters.variant)
	parameters.varPSF = "%s/variantSimulations/%s/structures/%s.%s.UNSOLVATED.psf" \
							% (parameters.runDIR, parameters.protein,
							   parameters.protein, parameters.variant)
	alignmentRes = parameters.alignmentResidues
	clusterRes = parameters.clusterResidues
	clustTCL = open(matrix ,"w")
	clustTCL.write("package require csv\n")
	for scaff in pdbs:
		clustTCL.write("mol addfile %s waitfor all\n" % scaff)

	#aligns the frames to the first frame
	clustTCL.write("set nf [molinfo top get numframes]\n")
	clustTCL.write("set refRes [atomselect top \""+alignmentRes+"\" frame 0]\n")
	clustTCL.write("set refStruct [atomselect top all frame 0]\n")
	clustTCL.write("for {set i 0} {$i < $nf} {incr i} {\n")
	clustTCL.write("  set curStruct [atomselect top all frame $i]\n")
	clustTCL.write("  set curRes [atomselect top \""+alignmentRes+"\" frame $i]\n")
	clustTCL.write("  set M [measure fit $curRes $refRes]\n")
	clustTCL.write("  $curStruct move $M\n")
	clustTCL.write("}\n")

	clustTCL.write("set output [open %s w]\n" % parameters.matrix)
	clustTCL.write("set back [atomselect top \""+clusterRes+"\" frame 0]\n")
	clustTCL.write("set refclustRes [atomselect top \""+clusterRes+"\" frame 0]\n")

	#calculates RMSD and writes to a file
	clustTCL.write("for {set i 0} {$i < $nf} {incr i} {\n")
	clustTCL.write("set row {}\n")
	clustTCL.write("for {set j 0} {$j < $nf} {incr j} {\n")
	clustTCL.write("$refclustRes frame $i \n")
	clustTCL.write("$back frame $j \n")
	clustTCL.write("set M [measure rmsd $back $refclustRes] \n")
	clustTCL.write("lappend row $M}\n")
	clustTCL.write("puts $output [::csv::join $row]}\n")

	clustTCL.write("close $output\n")
	clustTCL.write("quit")
	clustTCL.close()

	makeTableCommand = "%s -e %s" % (parameters.VMDpath, parameters.scaffoldTCL)
	os.system(makeTableCommand) 


def samplingNodes(parameters, tree):
	if not tree.child:
		if tree.extend:
			return [tree]
		else:
			return []
	bigList = []
	cur = [samplingNodes(parameters, x) for x in tree.child]
	for l in cur:
		bigList += l
	if tree.extend:
		bigList = (bigList + [tree]).sort(key=lambda x: x.num)
	else:
		bigList = bigList.sort(key=lambda x: x.num)
	return bigList

def main():
	parameters = argParse()
	parameters.setDefaults()

	parameters.num = 0
	top = samplingTree(parameters, parameters.num, parameters.newStruct, None)

	curList = samplingNodes(parameters, top)
	if curList:
		while curList:
			curscaff = curList.pop(0)
			runInstance(parameters, curscaff)
			curscaff.mark()
			if not checkStopCondition():
				scaffDir = "%s/variantSimulations/%s/results/%s/scaffold_%d" % (parameters.runDIR, parameters.protein, parameters.variant, curscaff.num)
				for file in os.listdir(scaffDir):
					if file.endswith("scaffold.pdb"):
						parameters.num += 1
						scaff = curRun + "/" + file
						curscaff.addChild(samplingTree(parameters, parameters.num, scaff, curscaff))
			curList = samplingNodes(parameters, top)

	print("Finished with sampling!")


main()






