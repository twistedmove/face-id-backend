from rest_framework.views import APIView
from rest_framework.response import Response
import cv2
from face_algorithm.id_utils import  calcCossimilarity, addFaceVec, calcEuclidDistance, deleteFaceVec
from django.conf import settings
from .my_serializers import RecognitionResultSerializer, RegisterSerializer, RecognitionRequestSerializer
from .models import Info
import os
from face_algorithm.joint_bayes_face import jointBayesVerify

# 特征向量提取算法选择
#from face_algorithm.face_id import getRep_openface
from face_algorithm.vgg_face import getRep_VGGface
getRep = getRep_VGGface
#getRep = getRep_openface


class FaceRecognition(APIView):

    def post(self, request, format=None):

        if len(settings.CANDIDATE) == 0:
            return Response({"detail":"No face in database!"})

        serializer = RecognitionRequestSerializer(data=self.request.data)

        data = serializer.valid_data
        imgArr = data["picture"]
        boundingbox = data["boundingbox"]
        threshold = data["threshold"]
        threshold = 0.8

        print("img:", imgArr.shape)
        print("bdbox:", boundingbox)
        print("threshold:", threshold)

        jointBayesThreshold = 400 # joint bayes的阈值，

        # 召回相似度最高的人
        try:
            resultId, similarity, v1, v2 = calcCossimilarity(imgArr, settings.CANDIDATE, getRep)
            #resultId, similarity = calcEuclidDistance(imgArr, settings.CANDIDATE)
        except:
            return Response({"detail": "recognition failed!"})

        print("resultId:", resultId)
        print("similarity:", similarity)
        if similarity >= threshold:
            info = Info.objects.get(ID=resultId)
            ID = info.ID
            name = info.name
            resImgPath = info.imgPath
            resSerializer = RecognitionResultSerializer(resImgPath, ID, name, similarity, True)

            # 使用joint bayes进行二次验证
            jointBayesScore = jointBayesVerify(v1, v2)
            print(jointBayesScore)
            if (jointBayesScore > jointBayesThreshold):
                return Response(resSerializer.valid_data)
            else:
                #resSerializer = RecognitionResultSerializer(None, similarity, False)
                return Response({"detail": "no result!"})
        else:
            return Response({"detail": "no result!"})


class Register(APIView):

    def post(self, request, format=None):

        serializer = RegisterSerializer(data=self.request.data)

        data = serializer.valid_data
        imgArr = data["picture"]
        del data["picture"]
        del data["boundingbox"]
        data["imgPath"] = settings.IMAGEPATH+str(data["ID"])+".jpg"
        try:
            # 储存数据库操作
            Info.objects.create(**data)
            # 生成图片操作
            cv2.imwrite(data["imgPath"], imgArr)
            # 生成特征向量并存储
            addFaceVec(imgArr, data["ID"], getRep)
        except:
            return Response({"detail": "Database Info saved Error!"})
        return Response({"detail": "new face has been saved!"})

class DeleteFace(APIView):

    def post(self, request, format=None):

        deleteID = self.request.data["delete_ID"]
        #try:
        # 获取图片路径
        info = Info.objects.get(ID=deleteID)
        deleteImgPath = info.imgPath
        # 删除特征向量
        deleteFaceVec(deleteID)
        # 删除图片文件
        os.remove(deleteImgPath)
        # 删除数据库记录
        Info.objects.get(ID=deleteID).delete()
        return Response({"detail": "delete success!"})

        #except:

            #return Response({"detail": "delete failed!"})



