import os
import sys
from PIL import Image

faultOffsetTolerance = 32
paddingBytesAfterResolution = 7

illusionString = '\x0CILLUSION3lib'

textureGroupString = '\x43TextureGroup'
multiTextureString = '\x43MultiTexture'
textureString = '\x43Texture'

nextFrameString = '\x05\x80'
nextMaterialString = '\x03\x80'
nextFolderString = '\x01\x80'

emitterGroupString = 'EmitterGroup'

flog = open('log.txt', 'w')
librariesPath = '0ext'
materialsPath = '1mat'

def locatePatternString(pat):
	pos = 0
	for i in range(len(pat)+faultOffsetTolerance):
		c = fin.read(1)

		if c == pat[pos]:
			pos += 1
			if pos == len(pat):
				pos = 0
				return True
		else:
			pos = 0
	return False

def locateEndingString(pat):
	pos = 0
	for i in range(len(pat)+faultOffsetTolerance):
		c = fin.read(1)

		if c == pat[pos]:
			pos += 1
			if pos == len(pat):
				pos = 0
				return 0 if i == len(pat)-1 else 1
		else:
			pos = 0
	return -1

def escapeName(name):
	temp = name.replace('\\', '_').replace('/', '_').replace(':', '_')
	temp = temp.replace('<', '_').replace('>', '_').replace('"', '_')
	temp = temp.replace('|', '_').replace('?', '_').replace('*', '_')
	return temp.replace('.', '_')

for root, dirs, files in os.walk(librariesPath):
	for file in files:
		if os.path.splitext(file)[1] != '.il3':
			continue

		print '>> File: '+root+'\\'+file
		print >> flog, '>> File: '+root+'\\'+file
		fin = open(root+'\\'+file, 'rb')

		# header of il3 file, 13 bytes
		if not locatePatternString(illusionString):
			print 'Error: no illusion header found'
			print >> flog, 'Error: no illusion header found'
			continue

		# how many material folders there are, 1 byte
		materialFolderNumber = ord(fin.read(1))

		# number should end with 0x00ff, 2 bytes
		if ord(fin.read(1)) != 0x00 or ord(fin.read(1)) != 0xff:
			print 'Error: file header not ends with 0x00ff'
			print >> flog, 'Error: file header not ends with 0x00ff'
			continue

		for mfn in range(materialFolderNumber):
			# first folder begins with TextureGroup string, 12 bytes
			if mfn == 0:
				# find TextureGroup string
				if not locatePatternString(textureGroupString):
					print 'Error: no texture group found'
					print >> flog, 'Error: no texture group found'
					break
			else:
				# other folder begin with certain pattern, says 0x0180
				temp = locateEndingString(nextFolderString)
				if temp == -1:
					print 'Error: no next folder found'
					print >> flog, 'Error: no next folder found'
					break
				elif temp == 1:
					print 'Warning: next folder string not tightly connected'
					print >> flog, 'Warning: next folder string not tightly connected'

			# how long this material folder name is, 1 byte
			materialFolderNameLength = ord(fin.read(1))
			# read the folder name
			folderName = ''
			for i in range(materialFolderNameLength):
				folderName += fin.read(1)
			# escape the folder name
			folderName = escapeName(folderName)
			print '\t>> Folder: '+folderName
			print >> flog, '\t>> Folder: '+folderName

			# make dir for this il3 material folder
			if not os.path.exists(materialsPath+'\\'+root+'\\'+os.path.splitext(file)[0]+'\\'+folderName+'\\'):
				os.makedirs(materialsPath+'\\'+root+'\\'+os.path.splitext(file)[0]+'\\'+folderName+'\\')

			# how many materials there are in this folder, 1 byte
			materialNumber = ord(fin.read(1))

			# padding after material number, 0x00 ,1 byte
			c = fin.read(1)

			for mn in range(materialNumber):
				# first material begins with MultiTexture string, 12 bytes
				if mfn == 0 and mn == 0:
					# find MultiTexture string
					if not locatePatternString(multiTextureString):
						print 'Error: no multi texture found'
						print >> flog, 'Error: no multi texture found'
						break
				else:
					# other materials begin with certain pattern, says 0x0380
					temp = locateEndingString(nextMaterialString)
					if temp == -1:
						print 'Error: no next material found'
						print >> flog, 'Error: no next material found'
						break
					elif temp == 1:
						print 'Warning: next material string not tightly connected'
						print >> flog, 'Warning: next material string not tightly connected'

				# how long this material name is, 1 byte
				materialNameLength = ord(fin.read(1))
				# read the folder name
				materialName = ''
				for i in range(materialNameLength):
					materialName += fin.read(1)
				print '\t\t>> Material: '+materialName
				print >> flog, '\t\t>> Material: '+materialName
				# escape the folder name
				materialName = escapeName(materialName)

				# how many frames this material have, 1 byte
				frameNumber = ord(fin.read(1))

				# padding after frame number, 0x00 ,1 byte
				c = fin.read(1)

				for fn in range(frameNumber):
					# NOT all frames begin with New Shape string
					# first frame of first material begins with Texture string
					if mfn == 0 and mn == 0 and fn == 0:
						# find Texture string
						if not locatePatternString(textureString):
							print 'Error: no texture found'
							print >> flog, 'Error: no texture found'
							break
					else:
						# other frames begin with certain pattern, says 0x0580
						temp = locateEndingString(nextFrameString)
						if temp == -1:
							print 'Error: no next frame found'
							print >> flog, 'Error: no next frame found'
							break
						elif temp == 1:
							print 'Warning: next frame string not tightly connected'
							print >> flog, 'Warning: next frame string not tightly connected'

					# how long this frame name is, 1 byte
					frameNameLength = ord(fin.read(1))
					# read the frame name, generally it will be New Shape
					frameName = ''
					for i in range(frameNameLength):
						frameName += fin.read(1)
					# escape the folder name
					frameName = escapeName(frameName)

					# depth: 0x01 for 32-bit, 0x00 for 8-bit, 1 byte
					depth = ord(fin.read(1))

					# resolution part, 10 bytes
					# for 256 width, surprising offset drift will happen, eg
					# 128*128 as 0x00000080, 0x00000080, 0x0000 but
					# 256*256 as 0x00000000, 0x01000000, 0x0100
					# it seems drift only happens for 256
					# width, 2 bytes in first 6 bytes
					width = 0
					for i in range(3):
						widthH = ord(fin.read(1))
						widthL = ord(fin.read(1))
						if widthH != 0 or widthL != 0:
							if width != 0:
								print 'Warning: width set more than 2 bytes in 6 bytes'
								print >> flog, 'Warning: width set more than 2 bytes in 6 bytes'
							width = widthH*256+widthL
					# height, 2 bytes in last 4 bytes
					height = 0
					for i in range(2):
						heightH = ord(fin.read(1))
						heightL = ord(fin.read(1))
						if heightH != 0 or heightL != 0:
							if height != 0:
								print 'Warning: height set more than 2 bytes in 6 bytes'
								print >> flog, 'Warning: height set more than 2 bytes in 6 bytes'
							height = heightH*256+heightL

					print '\t\t\t>> Frame: '+str(fn)+' Type: '+('RGBA' if depth else 'Grey')+' '+str(width)+'x'+str(height)+' Name: '+frameName
					print >> flog, '\t\t\t>> Frame: '+str(fn)+' Type: '+('RGBA' if depth else 'Grey')+' '+str(width)+'x'+str(height)+' Name: '+frameName

					# 8-bit or 32-bit, 2 bytes
					category = ord(fin.read(1))*256+ord(fin.read(1))
					# should stay consistent with depth
					if not (depth == 1 and category == 32) and not (depth == 0 and category == 8):
						print category
						print 'Error: depth/categroy not consistent'
						print >> flog, 'Error: depth/categroy not consistent'
						break

					# padding, 7 bytes
					for i in range(paddingBytesAfterResolution):
						c = fin.read(1)

					# read the frame
					pixArr = []
					for i in range(width*height):
						if depth:
							# RGBA
							pixR = ord(fin.read(1))
							pixG = ord(fin.read(1))
							pixB = ord(fin.read(1))
							pixA = ord(fin.read(1))
							pixArr.append((pixR, pixG, pixB, pixA))
						else:
							# Grey
							pix = ord(fin.read(1))
							pixArr.append((pix, pix, pix, pix))

					# build the image
					im = Image.new('RGBA', (width, height), (0, 0, 0, 0))
					im.putdata(pixArr)
					if frameNumber == 1:
						im.save(materialsPath+'\\'+root+'\\'+os.path.splitext(file)[0]+'\\'+folderName+'\\'+materialName+'.png')
						print '\t\t\t== Saved: '+materialsPath+'\\'+root+'\\'+os.path.splitext(file)[0]+'\\'+folderName+'\\'+materialName+'.png'
						print >> flog, '\t\t\t== Saved: '+materialsPath+'\\'+root+'\\'+os.path.splitext(file)[0]+'\\'+folderName+'\\'+materialName+'.png'
					else:
						im.save(materialsPath+'\\'+root+'\\'+os.path.splitext(file)[0]+'\\'+folderName+'\\'+materialName+'_'+format(fn, '02')+'.png')
						print '\t\t\t== Saved: '+materialsPath+'\\'+root+'\\'+os.path.splitext(file)[0]+'\\'+folderName+'\\'+materialName+'_'+format(fn, '02')+'.png'
						print >> flog, '\t\t\t== Saved: '+materialsPath+'\\'+root+'\\'+os.path.splitext(file)[0]+'\\'+folderName+'\\'+materialName+'_'+format(fn, '02')+'.png'

		#fin.close()

flog.close()